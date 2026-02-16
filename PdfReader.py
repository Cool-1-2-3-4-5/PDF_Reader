from google import genai
import pdfplumber as reader
import re
import os
import json
from dotenv import load_dotenv
from ddgs import DDGS
load_dotenv()


def orderganizeData(reorderedList, rawData):
    finalUpdatedList = []
    for company in rawData:
        tempList = ["0", "0", "0", "0", "0"]
        for column_entrie in range(len(reorderedList)):
            if reorderedList[column_entrie] == -1:
                tempList[column_entrie] = search(str(company[reorderedList[0]]), column_entrie)
            else:
                tempList[column_entrie] = company[reorderedList[column_entrie]]
        finalUpdatedList.append(tempList)
    return finalUpdatedList


def search(prompt, column):
    additional = ""
    if column == 1:
        additional = " address -site:yelp.com"
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
