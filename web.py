import streamlit as st
import pdfplumber as reader
import googlemaps
import json
import re
import os
import pandas as framework
from google import genai
from dotenv import load_dotenv
from PdfReader import orderganizeData, search, analyseDataGeminiWeb, text_cleaner, extract_table_robust

load_dotenv()

st.title("PDF Company Extractor")

main_password = os.getenv('PASSWORD') or st.secrets.get("PASSWORD")
st.session_state['main_password_active'] = False
def get_user_credentials():
    gemini_key = st.text_input("Enter your Gemini API Key:", type="password")
    if gemini_key:
        if gemini_key == main_password:
            gemini_key = os.getenv('GEMINI_KEY') or st.secrets.get("GEMINI_KEY")
            global main_password_active
            st.session_state['main_password_active'] = True
        try:
            client = genai.Client(api_key=gemini_key)
            response = client.models.generate_content(
                model='gemini-2.0-flash',
                contents='Say hello'
            )
            st.write("Key is valid!")
            st.session_state['gemini_key'] = gemini_key
        except Exception as e:
            st.write("Key is invalid or error occurred, Gemini integration will not work")
    if not st.session_state.get('file'):
        uploaded_file = st.file_uploader("Upload your PDF file (Only 1 file)", type="pdf")
        if uploaded_file:
            st.session_state['file'] = uploaded_file
            st.rerun()
    else:
        uploaded_file = st.session_state.get('file')
        st.write(uploaded_file.name)
    return gemini_key, uploaded_file
   
gemini_key, uploaded_file = get_user_credentials()

if st.session_state.get('file'):
    if st.button("Change file"):
        for key in ['file', 'keywords', 'keywords_valid', 'PROCESSED','entries_confirmed','starting_page','ending_page','pages_confirmed','starting_entrie', 'ending_entrie', 'preview_data', 'table_data', 'order_array', 'mainList', 'Data_organized', 'cached_keywords_maps', 'gemini_output', 'maps_key_validated']:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

if not gemini_key:
    st.warning("Please enter your Gemini API Key")
    st.stop()

if not uploaded_file:
    st.warning("Please upload a PDF file")
    st.stop()

loc = uploaded_file
if not st.session_state.get('keywords'):
    keywords = st.text_input("Enter what words you want to have and follow each word with a comma:")
    if keywords:
        keywords = keywords.split(",")
        st.session_state['keywords'] = keywords
        st.session_state['keywords_valid'] = True
        st.write(keywords)
        st.rerun()
else:
    st.write("You have selcted: " + str(st.session_state.get('keywords')))
    if st.button("Change keywords"):
        for key in ['keywords_valid','pages_confirmed','entries_confirmed', 'PROCESSED','gemini_output','maps_key_validated','starting_entrie', 'ending_entrie', 'preview_data', 'table_data', 'order_array', 'mainList', 'Data_organized', 'cached_keywords_maps', 'cached_keywords']:
            if key in st.session_state:
                del st.session_state[key]
        st.session_state['keywords'] = 0
        st.rerun()

mainList = []

if 'pages_confirmed' not in st.session_state:
    st.session_state['pages_confirmed'] = False
if 'entries_confirmed' not in st.session_state:
    st.session_state['entries_confirmed'] = False

with reader.open(loc) as pdf:
    total_pages = len(pdf.pages)
if st.session_state.get("keywords_valid"):
    if not st.session_state.get('pages_confirmed'):
        starting_page = st.number_input(
            "Based on your PDF, what page would you like to start with?",
            min_value=1,
            max_value=total_pages,
            value=1,
            step=1,
        )
        ending_page = st.number_input(
            "What page would you like to end with? For the last page, enter 0. Enter same first page number to only work on one page",
            min_value=0,
            max_value=total_pages,
            value=0,
            step=1,
        )
        if st.button("OK Pages"):
            if ending_page != 0 and ending_page < starting_page:
                st.write("Invalid. Starting page must be less than or equal to ending page")
            else:
                if ending_page != 0:
                    effective_ending_page = ending_page
                else:
                    effective_ending_page = total_pages
                st.session_state['starting_page'] = int(starting_page)
                st.session_state['ending_page'] = int(effective_ending_page)
                st.session_state['pages_confirmed'] = True
                st.session_state['entries_confirmed'] = False
                with reader.open(loc) as pdf:
                    page_obj = pdf.pages[int(starting_page) - 1]
                    data = extract_table_robust(page_obj)
                    if data:
                        for entrie in data:
                            rowList = []
                            for line in entrie:
                                line = str(line).replace("\n",", ")
                                rowList.append(line)
                            mainList.append(rowList)
                        st.session_state['preview_data'] = mainList
                        st.session_state['table_data'] = data
                    else:
                        st.warning("No table data found on this page. Try different page selection.")
            st.rerun()
    else:
        st.write("Starting Page: " + str(st.session_state.get('starting_page')) + " Ending Page: " + str(st.session_state.get('ending_page')))
        if st.button("Change Pages"):
            for key in ['entries_confirmed', 'PROCESSED', 'gemini_output', 'maps_key_validated', 'starting_entrie', 'ending_entrie', 'preview_data', 'table_data', 'order_array', 'mainList', 'Data_organized', 'cached_keywords_maps']:
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state['pages_confirmed'] = False
            st.rerun()


    if st.session_state.get('pages_confirmed') and 'preview_data' in st.session_state:
        starting_page = st.session_state.get('starting_page')
        effective_ending_page = st.session_state.get('ending_page')

        st.write(st.session_state.get('preview_data', []))
        st.write("")
        st.write("")

        if not st.session_state.get('entries_confirmed'):
            starting_entrie = st.number_input("Based on this preview, which entrie would you like to start with?", min_value=1, value=1)
            ending_entrie = st.number_input("Based on this preview, which entrie would you like to end with. For the last entrie, enter 0. Enter same first entrie number to only work on one entrie", min_value=0, value=0)

            if st.button("OK Entries"):
                if ending_entrie != 0 and ending_entrie < starting_entrie:
                    st.write("Invalid. Starting number must be less than ending number and ending number must fit between domain of data")
                elif ending_entrie > len(st.session_state.get('table_data', [])):
                    st.write("Invalid. Starting number must be less than ending number and ending number must fit between domain of data")
                else:
                    st.session_state['starting_entrie'] = int(starting_entrie)
                    st.session_state['ending_entrie'] = int(ending_entrie)
                    st.session_state['entries_confirmed'] = True
                st.rerun()
        else:
            st.write("Starting Entry: " + str(st.session_state.get('starting_entrie')) + " Ending Entry: " + str(st.session_state.get('ending_entrie')))
            if st.button("Change Entries"):
                for key in ['PROCESSED', 'gemini_output', 'order_array', 'mainList', 'Data_organized', 'cached_keywords_maps']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.session_state['entries_confirmed'] = False
                st.rerun()

        if st.session_state.get("entries_confirmed"):
            starting_entrie = st.session_state.get('starting_entrie')
            ending_entrie = st.session_state.get('ending_entrie')
            with reader.open(loc) as pdf:
                for page_obj in pdf.pages[int(starting_page)-1:int(effective_ending_page)]:
                    data = extract_table_robust(page_obj)
                    if not data:
                        continue
                    end_idx = ending_entrie-1 if ending_entrie != 0 else None
                    for entrie in data[starting_entrie-1:end_idx]:
                        rowList = []
                        for line in entrie:
                            line = str(line).replace("\n",", ")
                            rowList.append(line)
                        for word in st.session_state.get("keywords"):
                            for line in rowList:
                                if word.lower() in str(line).lower():
                                    mainList.append(rowList)
                                    break
                        rowList = []

            str_result = ""
            st.session_state['preview_data'] = mainList
            api_calls = len(mainList)
            estimated_cost = api_calls * 0.024
            st.info("Number of Companies: " + str(len(mainList)) + " | Maps API calls: " + str(2*api_calls) + " | Estimated cost: " + str(estimated_cost))
            
        if st.session_state.get('entries_confirmed') and (st.button("Process Companies") or "PROCESSED" in st.session_state):
            st.session_state['PROCESSED'] = True
            mainList = []
            starting_entrie = st.session_state.get('starting_entrie')
            ending_entrie = st.session_state.get('ending_entrie')
            mainList = st.session_state['preview_data']
            str_result = ""
            st.write(mainList)
            st.write("")
            st.write("")

            final = []
            if len(mainList) > 0:
                keywords = st.session_state.get('keywords')
                if "gemini_output" not in st.session_state or st.session_state.get('cached_keywords') != keywords:
                    gemini_prompt = """You are analyzing a company database entry. The data may be formatted as:
- Separate lines (one field per line)
- Comma-separated values
- Space-separated values
- Mixed/messy format

YOUR PRIMARY TASK: Identify the COMPANY NAME first (most important field). Then return column INDEX (0-based) for:
1. Company Name (names with Corp, Inc, Ltd, LLC, Company, Solutions, Tech, Group, etc.)
2. Address (street, city, postal code, state, country)
3. Phone Number (patterns like (XXX)XXX-XXXX, XXX-XXX-XXXX, +X-XXX-XXXX, ext., extension)
4. LinkedIn (URLs with linkedin.com, LinkedIn ID, or profile links)
5. Website URL (http/https or domain.com, .io, .net, .org patterns)

RESPONSE FORMAT: Return ONLY a JSON array with exactly 5 integers. Return -1 if a field is completely absent.
Example: [0, 1, 3, 2, 4]

EXAMPLES:

Example 1 - Separate lines (each element on own line):
Input:
Acme Corp
123 Main St
555-1234
linkedin.com/company/acme
acme.com
Output: [0, 1, 2, 3, 4]

Example 2 - Single entry, company name critical:
Input:
Acme Corporation | 456 Oak Avenue | (333) 555-2222 | linkedin.com/acme | acme.com
Output: [0, 1, 2, 3, 4]

Example 3 - Reordered with company identifier in middle:
Input:
(444) 555-3333
www.globaltech.io
GlobalTech Solutions Inc
789 Park Lane, Denver CO
linkedin.com/company/globaltech
Output: [2, 3, 0, 4, 1]

Example 4 - Missing LinkedIn:
Input:
Tech Solutions Ltd
456 Oak Ave, NY
(222) 555-9876
Not provided
www.techsol.com
Output: [0, 1, 2, -1, 4]

Example 5 - Messy single line (identify company name first):
Input:
ABC Industries | Phone: (555) 888-2222 | Address: 123 Commerce St | Web: abcindustries.com | No LinkedIn
Output: [0, 2, 1, -1, 3]

Example 6 - Company name among numbers (company is identifiable):
Input:
Email: contact@xyz.com
555-6666
123 Business Plaza
XYZ Solutions
linkedin.com/company/xyz-solutions
Output: [3, 2, 1, 4, -1]

CRITICAL RULES:
- PRIORITY: Always identify Company Name FIRST - it's the anchor point
- Return ONLY the JSON array, NO other text
- Company identifiers: Corp, Inc, Ltd, LLC, Company, Solutions, Tech, Group, Industries, Services, Global, International, etc.
- If company name is ambiguous between multiple candidates, pick the one containing business-type keywords
- Phone: Look for digits with () or - or ext/extension
- Website: Ends with domain extension (.com, .io, .net, .org, etc.) or starts with http/www
- LinkedIn: Contains "linkedin" or profile link patterns
- Address: Contains street patterns (St, Ave, Blvd, Road, Lane, etc.) or city/state indicators
- If a field appears messy/unclear, still identify its column index (-1 ONLY if completely missing)
"""
                    gemini_output, TimedOut = analyseDataGeminiWeb(gemini_prompt, mainList[0], gemini_key)
                    if not TimedOut:
                        order_array = text_cleaner(gemini_output.text)
                        st.session_state['order_array'] = order_array
                        st.session_state['cached_keywords'] = keywords
                        st.session_state['gemini_output'] = True
                        result_parts = []
                        if order_array[0] != -1:
                            result_parts.append("Company found")
                        if order_array[1] != -1:
                            result_parts.append("Address found")
                        if order_array[2] != -1:
                            result_parts.append("Phone Number found")
                        if order_array[3] != -1:
                            result_parts.append("LinkedIn found")
                        if order_array[4] != -1:
                            result_parts.append("Company Website found")
                        st.write(", ".join(result_parts))
                        st.session_state['mainList'] = mainList
                else:
                    order_array = st.session_state.get('order_array')
                    mainList = st.session_state.get('mainList')
            else:
                st.write("No companies found")

    if 'order_array' in st.session_state:
        if st.session_state.get('order_array'):
            order_array = st.session_state.get('order_array')
            mainList = st.session_state.get('mainList')
            keywords = st.session_state.get('cached_keywords', "")
            
            if not st.session_state['main_password_active']: # not DSQ
                password_for_maps = st.text_input("MAPS API Please:", type="password")
                if password_for_maps:
                    if 'maps_key_validated' not in st.session_state or st.session_state.get('cached_keywords_maps') != keywords:
                        try:
                            maps_access = googlemaps.Client(password_for_maps)
                            st.write("Key is valid!")
                            re_ordered_array = orderganizeData(order_array, mainList, password_for_maps)
                            st.session_state['Data_organized'] = re_ordered_array
                            st.session_state['maps_key_validated'] = True
                            st.session_state['cached_keywords_maps'] = keywords
                        except Exception as e:
                            st.write("Key is invalid or error occurred, Maps integration will not work. Alt to DDGS")
                            re_ordered_array = orderganizeData(order_array, mainList, "DDGS")
                            st.session_state['Data_organized'] = re_ordered_array
                            st.session_state['maps_key_validated'] = True
                            st.session_state['cached_keywords_maps'] = keywords
                    else:
                        # Maps already processed for these keywords, retrieve cached data
                        pass
            else:
                if 'maps_key_validated' not in st.session_state or st.session_state.get('cached_keywords_maps') != keywords:
                    maps_api_key = os.getenv('MAPS_KEY') or st.secrets.get("MAPS_KEY")
                    re_ordered_array = orderganizeData(order_array, mainList, maps_api_key)
                    st.session_state['Data_organized'] = re_ordered_array
                    st.session_state['maps_key_validated'] = True
                    st.session_state['cached_keywords_maps'] = keywords
                else:
                    # Maps already processed for these keywords, retrieve cached data
                    pass
    if 'Data_organized' in st.session_state:
        final = st.session_state.get('Data_organized')
        st.write("")
        st.write("")
        st.write(final)
        data = framework.DataFrame(
            final,
            columns=["Company Name", "Address", "Phone Number", "LinkedIn", "Website", "Issues"],
        )
        st.code(data.to_csv(sep='\t', index=False, quoting=1), language="text")