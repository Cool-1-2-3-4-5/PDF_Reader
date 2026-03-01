from google import genai
import pdfplumber as reader
import os
import googlemaps
import re
import os
import json
from dotenv import load_dotenv
from ddgs import DDGS
load_dotenv()


def extract_table_robust(page):
    """
    Try multiple methods to extract table data from a PDF page.
    Returns a list of rows, or None if no data found.
    """
    # Method 1: Try standard table extraction
    table = page.extract_table()
    if table and len(table) > 0:
        return table
    
    # Method 2: Try extracting all tables and merge them
    tables = page.extract_tables()
    if tables and len(tables) > 0:
        merged = []
        for t in tables:
            if t:
                merged.extend(t)
        if merged:
            return merged
    
    # Method 3: Try with different table settings for borderless tables
    table_settings = {
        "vertical_strategy": "text",
        "horizontal_strategy": "text",
        "snap_tolerance": 5,
        "join_tolerance": 5,
    }
    table = page.extract_table(table_settings)
    if table and len(table) > 0:
        return table
    
    # Method 4: Try with lines-based detection
    table_settings_lines = {
        "vertical_strategy": "lines",
        "horizontal_strategy": "lines",
    }
    table = page.extract_table(table_settings_lines)
    if table and len(table) > 0:
        return table
    
    # Method 5: Fall back to text extraction and parse into rows
    text = page.extract_text()
    if text:
        lines = text.strip().split('\n')
        # Try to split each line by common delimiters
        parsed_rows = []
        for line in lines:
            if line.strip():
                # Try tab first, then multiple spaces
                if '\t' in line:
                    row = line.split('\t')
                elif '  ' in line:  # Multiple spaces
                    row = re.split(r'\s{2,}', line)
                else:
                    row = [line]
                parsed_rows.append(row)
        if parsed_rows:
            return parsed_rows
    
    return None


def extract_with_ai_fallback(page, api_key):
    """
    Use AI to extract structured data from raw PDF text when table extraction fails.
    """
    text = page.extract_text()
    if not text:
        return None
    
    client = genai.Client(api_key=api_key)
    prompt = """Extract company information from this text and return as a JSON array of arrays.
Each inner array should contain columns of data found in the text.
If the text appears to be tabular data, preserve the row/column structure.
Return ONLY the JSON array, no explanation.

Text:
""" + text
    
    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
        )
        return text_cleaner(response.text)
    except Exception:
        return None


def orderganizeData(reorderedList, rawData,maps_api):
    finalUpdatedList = []
    for company_info in rawData:
        tempList = ["-1", "-1", "-1", "-1", "-1"]
        if maps_api != "DDGS":
            main_List = maps_search(str(company_info[reorderedList[0]]),maps_api)
            if len(main_List) != 0: # google maps worked
                tempList = main_List
                print("WORKED")
            print(company_info[reorderedList[0]])
            print(tempList)
            print(reorderedList)
            for column_entrie in range(len(reorderedList)):
                if reorderedList[column_entrie] == -1 and tempList[column_entrie] == "-1": # not in data or google maps
                    print("MAPS: " + str(column_entrie))
                    tempList[column_entrie] = search(str(company_info[reorderedList[0]]), column_entrie)
                elif reorderedList[column_entrie] == -1 and tempList[column_entrie] != -1: #  not in data but in google maps
                    pass
                else: #  in data but not in google maps OR in data and in google maps
                    tempList[column_entrie] = company_info[reorderedList[column_entrie]]
        else: # KEY unavlible
            for column_entrie in range(len(reorderedList)):
                if reorderedList[column_entrie] == -1: # not in data or google maps
                    print("DDGS: " + str(column_entrie))
                    tempList[column_entrie] = search(str(company_info[reorderedList[0]]), column_entrie)
                else: #  in data 
                    tempList[column_entrie] = company_info[reorderedList[column_entrie]]
        finalUpdatedList.append(tempList)
    return finalUpdatedList

def maps_search(company_name,api_key):
    maps_access = googlemaps.Client(api_key)
    results = maps_access.find_place(input = company_name,input_type="textquery")
    if results:
        details = maps_access.place(results['candidates'][0]['place_id'])
        full_list = []
        if 'name' in details['result']:
            full_list.append(details['result']['name'])
        else:
            full_list.append("-1")
        if 'vicinity' in details['result']:
            full_list.append(details['result']['vicinity'])
        else:
            full_list.append("-1")
        if 'international_phone_number' in details['result']:
            full_list.append(details['result']['international_phone_number'])
        else:
            full_list.append("-1")
        full_list.append("-1") # LinkinIn
        if 'website' in details['result']:
            full_list.append(details['result']['website'])
        else:
            full_list.append("-1")
        return full_list
    else:
        return []


def search(prompt, column):
    additional = ""
    if column == 1:
        additional = " site:google.com/maps"
    elif column == 2:
        additional = " Phone Number"
    elif column == 3:
        additional = " site:linkedin.com/company/"
    elif column == 4:
        additional = " -site:wikipedia.org -site:facebook.com -site:instagram.com"
    else:
        pass
    result = DDGS().text((prompt + additional), region='wt-wt', backend='api', max_results=5)
    if result:
        phone_pattern_first_check = r"(\+?\d{1,2}\s?)?(\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4})"
        phone_pattern_second_check = re.compile("""
(\+1\ ?)? # optional +1 and space
\(?       # optional (
[0-9]{3}
\)?       # optional )
[- ]?     # optional - or space
[0-9]{3}
-?        # optional -
[0-9]{4}
""", flags=re.VERBOSE)
        if column == 2:
            for option in result:
                phone_number = option["body"]
                match = re.search(phone_pattern_first_check, phone_number)
                if match:
                    possible_number = match.group(0).strip()
                    numbers = phone_pattern_second_check.findall(possible_number)
                    if numbers:
                        return possible_number
            return None
        elif column == 4:
            for option in result:
                company_link = option["href"]
                company_link = company_link.lower()
                if ("wikipedia" not in company_link) and ("facebook" not in company_link) and ("instagram" not in company_link):
                    return company_link
            return None
        else:
            return result[0]["href"]


def analyseDataGeminiWeb(prompt, data, api_key):
    client = genai.Client(api_key=api_key)
    formatted_data = "\n".join([str(row) for row in data])
    full_promt = prompt + "\n Here is the formatted data: " + formatted_data
    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=full_promt,
        )
        return response, False
    except Exception as exit:
        return None, True


def text_cleaner(raw_text):
    match = re.search(r'\[.*\]', raw_text, re.DOTALL)
    final_array = json.loads(match.group(0))
    return final_array
