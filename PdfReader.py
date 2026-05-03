import google.genai as genai
import pdfplumber as reader
import os
import googlemaps
import re
import json
from dotenv import load_dotenv
from ddgs import DDGS
load_dotenv()


def extract_table_robust(page):   
    # Method 1: Standard table extraction
    table = page.extract_table()
    if table and len(table) > 0:
        return table
    
    # Method 2: Extracting all tables and merge them
    tables = page.extract_tables()
    if tables and len(tables) > 0:
        merged = []
        for t in tables:
            if t:
                merged.extend(t)
        if merged:
            return merged
    
    # Method 3: Configure table settings for borderless tables
    table_settings = {
        "vertical_strategy": "text",
        "horizontal_strategy": "text",
        "snap_tolerance": 5,
        "join_tolerance": 5,
    }
    table = page.extract_table(table_settings)
    if table and len(table) > 0:
        return table
    
    # Method 4: Lines-based detection
    table_settings_lines = {
        "vertical_strategy": "lines",
        "horizontal_strategy": "lines",
    }
    table = page.extract_table(table_settings_lines)
    if table and len(table) > 0:
        return table
    
    # Method 5: Text extraction and parse into rows
    text = page.extract_text()
    if text:
        lines = text.strip().split('\n')
        # Split each line
        parsed_rows = []
        for line in lines:
            if line.strip():
                # Tab first
                if '\t' in line:
                    row = line.split('\t')
                elif '  ' in line: # Multiple spaces
                    row = re.split(r'\s{2,}', line)
                else:
                    row = [line]
                parsed_rows.append(row)
        if parsed_rows:
            return parsed_rows
    return None

def orderganizeData(reorderedList, rawData,maps_api):
    finalUpdatedList = []
    if not rawData:
        return finalUpdatedList
    
    for company_info in rawData:
        tempList = ["-1", "-1", "-1", "-1", "-1"]
        
        if not company_info or len(company_info) == 0:
            finalUpdatedList.append(tempList)
            continue
        
        try:
            # Safety
            if reorderedList[0] != -1 and reorderedList[0] < len(company_info):
                company_name = str(company_info[reorderedList[0]])
            else:
                company_name = str(company_info[0])
        except:
            company_name = "Unknown/Error"
        if company_name == "Unknown/Error": # Issue
            pass
        elif maps_api != "DDGS":
            main_List,maps_api_issue = maps_search(company_name, maps_api)

            if len(main_List) != 0: # Google Maps worked
                tempList = main_List
            if company_info != main_List:
                for column_entrie in range(len(reorderedList)):
                    if reorderedList[column_entrie] == -1 and tempList[column_entrie] == "-1": # Not in data OR not in google maps
                        verify = search(company_name, column_entrie)
                        if verify:
                            tempList[column_entrie] = verify
                        else:
                            tempList[column_entrie] = "Error"
                    elif tempList[column_entrie] == "-1" and reorderedList[column_entrie] != -1: # In data but not in google maps OR in data and in google maps
                        tempList[column_entrie] = "In Data"
                    else: # Nothing to change
                        pass
            else:
                tempList = ["COULD NOT FIND: ", str(company_info), "", "", ""]
            if maps_api_issue == "Untrieble":
                tempList.append("All Data was not found through Maps API")
            elif maps_api_issue == "Error":
                tempList.append("Maps API does not work")
            else:
                tempList.append("")
        else: # Key unavailable
            for column_entrie in range(len(reorderedList)):
                if reorderedList[column_entrie] == -1: # Not in data OR google maps
                    # Use Company Name instead which was safely retrieved
                    verify = search(company_name, column_entrie)
                    if verify:
                        tempList[column_entrie] = verify
                    else:
                        tempList[column_entrie] = "Error"
                else: # In data 
                    tempList[column_entrie] = "NEED TO FIND"
        finalUpdatedList.append(tempList)
    return finalUpdatedList

def maps_search(company_name,api_key):
    try:
        maps_access = googlemaps.Client(api_key)
        results = maps_access.find_place(input = company_name,input_type="textquery")
        if results and results.get('candidates') and len(results['candidates']) > 0:
            details = maps_access.place(results['candidates'][0]['place_id'])
            if 'result' not in details:
                return [company_name], "Untrieble"
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
                num = (details['result']['international_phone_number']).replace("+","")
                full_list.append(num)
            else:
                full_list.append("-1")
            full_list.append("-1") # LinkedIn
            if 'website' in details['result']:
                full_list.append(details['result']['website'])
            else:
                full_list.append("-1")
            return full_list, "Good"
        else:
            return [company_name], "Untrieble"
    except:
        return [company_name], "Error"


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
    else: # Nothing to change
        pass
    
    result = None
    try:
        result = DDGS().text((prompt + additional), region='wt-wt', backend='api', max_results=5)
    except:
        pass
    if result:
        phone_pattern_first_check = r"(\+?\d{1,2}\s?)?(\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4})"
        phone_pattern_second_check = re.compile(r"""
        (\+1\ ?)?
        \(?
        [0-9]{3}
        \)?
        [- ]?
        [0-9]{3}
        -?
        [0-9]{4}
        """, flags=re.VERBOSE)
        if column == 2:
            for option in result:
                if "body" not in option:
                    continue
                phone_number = option["body"]
                match = re.search(phone_pattern_first_check, phone_number)
                if match:
                    possible_number = match.group(0).strip()
                    numbers = phone_pattern_second_check.findall(possible_number)
                    if numbers:
                        possible_number = possible_number.replace("o","")
                        return possible_number
            return None
        elif column == 4:
            for option in result:
                if "href" not in option:
                    continue
                company_link = option["href"]
                company_link = company_link.lower()
                if ("wikipedia" not in company_link) and ("facebook" not in company_link) and ("instagram" not in company_link):
                    return company_link
            return None
        else:
            if result and len(result) > 0 and "href" in result[0]:
                return result[0]["href"]
            else:
                return None
    else:
        return None


def analyseDataGeminiWeb(prompt, data, api_key=None):
    # Use Google Generative AI API
    try:
        # Create client with the API key
        client = genai.Client(api_key=api_key)
        formatted_data = "\n".join([str(row) for row in data])
        full_promt = prompt + "\n Here is the formatted data: " + formatted_data
        
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=full_promt,
            config={
                'temperature': 0,
                'top_p': 0.95,
                'top_k': 40,
            }
        )
        print(f"[DEBUG] Gemini API response received: {response.text[:100]}")
        return response, False
    except Exception as e:
        print(f"[DEBUG] Gemini API error: {str(e)}")
        return None, True


def text_cleaner(raw_text):
    try:
        match = re.search(r'\[.*\]', raw_text, re.DOTALL)
        if not match:
            return []
        final_array = json.loads(match.group(0))
        return final_array
    except:
        return [-1,-1,-1,-1,-1]
