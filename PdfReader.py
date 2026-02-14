from google import genai
import serpapi
import pdfplumber as reader
import re
import os
import json
from dotenv import load_dotenv
from ddgs import DDGS
load_dotenv()

gemini_key = os.getenv('GEMINI_KEY')
file_name = os.getenv('FILE_NAME')

client = genai.Client(api_key=gemini_key)

def orderganizeData(reorderedList,rawData):
    finalUpdatedList = []
    for company in rawData:
        tempList = ["0","0","0","0","0"]
        for column_entrie in range(len(reorderedList)):
            if reorderedList[column_entrie] == -1:
                print("NO")
                tempList[column_entrie] = search(str(company[reorderedList[0]]),column_entrie)
                pass
                # this is the api call
            else:
                print("ALR Exist")
                tempList[column_entrie] = company[reorderedList[column_entrie]]
        finalUpdatedList.append(tempList)
    return finalUpdatedList

def search(prompt,column):
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
    result = DDGS().text((prompt+additional),region='wt-wt',backend='api',max_results=5)
    if result:
        phone_pattern = r"(\+?\d{1,2}\s?)?(\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4})"
        company_pattern = "www"
        if column == 2:
            for option in result:
                phone_number = option["body"]
                match = re.search(phone_pattern, phone_number) 
                if match:
                    return match.group(0).strip() 
            return None
        elif column == 4: #company website
            for option in result:
                print(option["href"])
            for option in result:
                company_link = option["href"]
                print(company_link)
                if company_pattern in company_link.lower():
                    return company_link
                return None
        else:
            # company_link = option["href"]
            # print(company_link)
            # match = re.search(company_pattern, company_link)
            return result[0]["href"]
            

def analyseDataGemini(prompt, data):
    formatted_data = "\n".join([str(row) for row in data])
    full_promt = prompt + "\n Here is the formatted data: " + formatted_data
    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash', 
            contents= full_promt,
        )
        return response,False
    except Exception as exit:
        if "429" in str(exit):
            print("API TIME OUT")
        return None,True
def text_cleaner(raw_text):
    match = re.search(r'\[.*\]', raw_text, re.DOTALL)
    final_array = json.loads(match.group(0))
    return final_array


loc = file_name
keywords = input("Enter what words you wanna have followed by comma: ")
keywords = keywords.split(",")
print(keywords)
mainList = []

page = input("Enter what page you want to start, followed by a comma, what page you want to end: ").split(",")
while len(page) != 2 or int(page[0]) <= 0 or int(page[1]) <= 0:
    print("Try Again, incorrect values or format")
    page = input("Enter what page you want to start, followed by a comma, what page you want to end: ").split(",")
starting_page = int(page[0])
ending_page = int(page[1])

with reader.open(loc) as pdf:
    # Use for Preview
    page = pdf.pages[starting_page-1]
    data = page.extract_table()
    for entrie in data:
        rowList = []
        for line in entrie: # cleaning up
            line = str(line).replace("\n",", ")
            rowList.append(line)
        mainList.append(rowList)
    for entrie in mainList: # cleaning up
        print(entrie)
    print("\n\n\n\n\n\n\n")
    starting_entrie = int(input("Based on this preview, which entrie would you like to start with?: "))
    ending_entrie = int(input("Based on this preview, which entrie would you like to end with. If no preference please enter 0?: "))
    while (ending_entrie < starting_entrie and ending_entrie != 0) or ending_entrie > len(data) :
        print("invalid. Starting number must be less than ending number adn ending number must fit between domain of data")
        starting_entrie = int(input("Based on this preview, which entrie would you like to start with?: "))
        ending_entrie = int(input("Based on this preview, which entrie would you like to end with. If no preference please enter 0?: "))
    
    # Automation
    mainList = []
    for page in pdf.pages[starting_page-1:ending_page-1]:
        data = page.extract_table()
        for entrie in data[starting_entrie-1:ending_entrie-1]:
            rowList = []
            for line in entrie: # cleaning up
                line = str(line).replace("\n",", ")
                rowList.append(line)
            for word in keywords:
                for line in rowList:
                    if word.lower() in str(line).lower():
                        mainList.append(rowList)
                        break
        rowList = []
    
print(mainList)
print("\n\n\n\n\n\n\n")
final= []
if len(mainList) > 0:
    gemini_output,TimedOut = analyseDataGemini("Here is a company entry, based on this entry Find where the CompanyName, Address, Phone number, Linkedid, and Website are located. I might give you more than 5 or less than 5 entries. Return a 1D JSON format array with the number corresponding to place where that information is found in the entrie: Example if Phone number is on 6 column in the raw data, then return 5 in 4th index of array. Start at 0. If any of these info is not found return -1 for that entrie. Your ouput hould only be that array no talking", mainList[0])
    if not TimedOut:
        order_array = text_cleaner(gemini_output.text)
        print(order_array)
        re_ordered_array = []
        re_ordered_array = orderganizeData(order_array,mainList)
        final = re_ordered_array
else:
    print("No companies found")
print("\n\n\n\n\n\n\n")
print(final)

with open("data.json","w") as file:
    json.dump(final,file,indent=4)

print("\n\n\n\n\n\n\n")
print("Succesfulley updated JSON")

# Here is the list of columns. Analyse the data and reorder the entries to fit this order: CompanyName, Address, Phone number(If not found in the data, Replace with N/A), Linkedin(If not found in the data, Replace with N/A),  Company Website(If not found in the data, Replace with N/A). If any of this information is not retriable, write the entrie with N/A. Return your response as a JSON array of arrays (matrix format). Example: [['Company1', 'Address1', 'Phone1', 'LinkedIn1', 'Website1'], ['Company2', 'Address2', 'Phone2', 'LinkedIn2', 'Website2]]. Return ONLY the JSON array, no other text.



# def analyseDataWeb(json_matrix):
    # updated_List = []
    # for raw_row in json_matrix:
    #     row = list(raw_row)
    #     company = row[0]
    #     address = row[1]
    #     top_results = []
    #     try:
    #         web_result = webscraper.search(
    #             q=company,
    #             engine="google",
    #             location=address,
    #             hl="en"
    #         )
    #         top_results = web_result["organic_results"]
    #     except Exception:
    #         top_results = []
    #     if row[4] == "N/A" and top_results:
    #         row[4] = top_results[0]["link"]
    #     if row[3] == "N/A" and top_results:
    #         for entrie in top_results[:10]:
    #             if "linkedin" in entrie["link"].lower():
    #                 row[3] = entrie["link"]
    #                 break
    #     if row[2] == "N/A":
    #         try:
    #             maps_result = webscraper.search(
    #                 q=company,
    #                 engine="google_maps",
    #                 location=address,
    #                 type="search"
    #             )
    #             maps_data = maps_result["local_results"]
    #             if maps_data:
    #                 row[2] = (maps_data[0])["phone"]
    #         except Exception:
    #             pass

    #     updated_List.append(row)
    # return updated_List




    # for page in pdf.pages:
    #     data = page.extract_table()
    #     coluumn_names = data[1]
    #     for entrie in data[2:]:
    #         rowList = []
    #         for line in entrie: # cleaning up
    #             line = str(line).replace("\n",", ")
    #             rowList.append(line)
    #         for word in keywords:
    #             for line in rowList:
    #                 if (word.lower() or word.upper()) in (str(line).lower() or str(line).upper()):
    #                     mainList.append(rowList)
    #                     break