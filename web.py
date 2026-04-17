import streamlit as st
import pdfplumber as reader
import googlemaps
import json
import re
import os
import pandas as framework
from google import genai
from dotenv import load_dotenv
from PdfReader import orderganizeData, search, analyseDataGeminiWeb, text_cleaner

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
    
    uploaded_file = st.file_uploader("Upload your PDF file (Only 1 file)", type="pdf")
    st.session_state['file'] = uploaded_file
    return gemini_key, uploaded_file
   
gemini_key, uploaded_file = get_user_credentials()

if st.session_state.get('file'):
    if st.button("Change file"):
        for key in ['PROCESSED','entries_confirmed','starting_page','ending_page','pages_confirmed','starting_entrie', 'ending_entrie', 'preview_data', 'table_data', 'order_array', 'mainList', 'Data_organized', 'cached_keywords_maps']:
            if key in st.session_state:
                del st.session_state[key]

if not gemini_key:
    st.warning("Please enter your Gemini API Key")
    st.stop()

if not uploaded_file:
    st.warning("Please upload a PDF file")
    st.stop()

loc = uploaded_file

keywords = st.text_input("Enter what words you wanna have followed by comma:")
keywords = keywords.split(",")
st.session_state['keywords'] = True
st.write(keywords)

mainList = []

if 'pages_confirmed' not in st.session_state:
    st.session_state['pages_confirmed'] = False
if 'entries_confirmed' not in st.session_state:
    st.session_state['entries_confirmed'] = False

with reader.open(loc) as pdf:
    total_pages = len(pdf.pages)

starting_page = st.number_input(
    "Based on your PDF, which page would you like to start with?",
    min_value=1,
    max_value=total_pages,
    value=1,
    step=1,
)
ending_page = st.number_input(
    "Which page would you like to end with? If no preference, enter 0",
    min_value=0,
    max_value=total_pages,
    value=0,
    step=1,
)

if not st.session_state.get('pages_confirmed'):
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
                data = page_obj.extract_table()
                for entrie in data:
                    rowList = []
                    for line in entrie:
                        line = str(line).replace("\n",", ")
                        rowList.append(line)
                    mainList.append(rowList)
                st.session_state['preview_data'] = mainList
                st.session_state['table_data'] = data
else:
    if st.button("Change Pages"):
        if ending_page != 0 and ending_page < starting_page:
            st.write("Invalid. Starting page must be less than or equal to ending page")
        else:
            st.session_state['entries_confirmed'] = False
            st.session_state['PROCESSED'] = False
            st.session_state['gemini_output'] = False
            st.session_state['maps_key_validated'] = False
            
            # Delete downstream states
            for key in ['starting_entrie', 'ending_entrie', 'preview_data', 'table_data', 'order_array', 'mainList', 'Data_organized', 'cached_keywords_maps']:
                if key in st.session_state:
                    del st.session_state[key]
            if ending_page != 0:
                effective_ending_page = ending_page
            else:
                effective_ending_page = total_pages
            st.session_state['starting_page'] = int(starting_page)
            st.session_state['ending_page'] = int(effective_ending_page)
            st.session_state['pages_confirmed'] = True
            with reader.open(loc) as pdf:
                page_obj = pdf.pages[int(starting_page) - 1]
                data = page_obj.extract_table()
                for entrie in data:
                    rowList = []
                    for line in entrie:
                        line = str(line).replace("\n",", ")
                        rowList.append(line)
                    mainList.append(rowList)
                st.session_state['preview_data'] = mainList
                st.session_state['table_data'] = data


if st.session_state.get('pages_confirmed') and 'preview_data' in st.session_state:
    starting_page = st.session_state.get('starting_page')
    effective_ending_page = st.session_state.get('ending_page')

    for entrie in st.session_state.get('preview_data', []):
        st.write(entrie)
    st.write("")
    st.write("")

    if not st.session_state.get('entries_confirmed'):
        starting_entrie = st.number_input("Based on this preview, which entrie would you like to start with?", min_value=1, value=1)
        ending_entrie = st.number_input("Based on this preview, which entrie would you like to end with. If no preference please enter 0", min_value=0, value=0)

        if st.button("OK Entries"):
            if ending_entrie != 0 and ending_entrie < starting_entrie:
                st.write("invalid. Starting number must be less than ending number and ending number must fit between domain of data")
            elif ending_entrie > len(st.session_state.get('table_data', [])):
                st.write("invalid. Starting number must be less than ending number and ending number must fit between domain of data")
            else:
                st.session_state['starting_entrie'] = int(starting_entrie)
                st.session_state['ending_entrie'] = int(ending_entrie)
                st.session_state['entries_confirmed'] = True
    else:
        if st.button("Change Entries"):
            for key in ['PROCESSED','preview_data', 'table_data', 'order_array', 'mainList', 'Data_organized', 'cached_keywords_maps']:
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state['entries_confirmed'] = False

        
    if st.session_state.get('entries_confirmed') and (st.button("Process Companies") or "PROCESSED" in st.session_state):
        st.session_state['PROCESSED'] = True
        mainList = []
        starting_entrie = st.session_state.get('starting_entrie')
        ending_entrie = st.session_state.get('ending_entrie')
        with reader.open(loc) as pdf:
            for page_obj in pdf.pages[int(starting_page)-1:int(effective_ending_page)]:
                data = page_obj.extract_table()
                end_idx = ending_entrie-1 if ending_entrie != 0 else None
                for entrie in data[starting_entrie-1:end_idx]:
                    rowList = []
                    for line in entrie:
                        line = str(line).replace("\n",", ")
                        rowList.append(line)
                    for word in keywords:
                        for line in rowList:
                            if word.lower() in str(line).lower():
                                mainList.append(rowList)
                                break
                    rowList = []

        str_result = ""
        st.write(mainList)
        st.write("")
        st.write("")

        final = []
        if len(mainList) > 0:
            if "gemini_output" not in st.session_state or st.session_state.get('cached_keywords') != keywords:
                gemini_output, TimedOut = analyseDataGeminiWeb("Here is a company entry, based on this entry Find where the CompanyName, Address, Phone number, Linkedid, and Website are located. I might give you more than 5 or less than 5 entries. Return a 1D JSON format array with the number corresponding to place where that information is found in the entrie: Example if Phone number is on 6 column in the raw data, then return 5 in 4th index of array. Start at 0. If any of these info is not found return -1 for that entrie. Your ouput hould only be that array no talking", mainList[0], gemini_key)
                if not TimedOut:
                    print("Gemini Entered")
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
                    
        print("!EN")
        if not st.session_state['main_password_active']: # not DSQ
            password_for_maps = st.text_input("MAPS API Please:", type="password")
            print(password_for_maps)
            if password_for_maps:
                if 'maps_key_validated' not in st.session_state or st.session_state.get('cached_keywords_maps') != keywords:
                    print("ENTERED")
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
                        print("HERE")
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
                print("EXIT")
            else:
                # Maps already processed for these keywords, retrieve cached data
                pass
print("ENTER")
if 'Data_organized' in st.session_state:
    final = st.session_state.get('Data_organized')
    print("in")
    st.write("")
    st.write("")
    st.write(final)
    data = framework.DataFrame(
        final,
        columns=["Company Name", "Address", "Phone Number", "LinkedIn", "Website"],
    )
    st.code(data.to_csv(sep='\t', index=False, quoting=1), language="text")