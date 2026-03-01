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

password_for_gemini_key = os.getenv('PASSWORD')

def get_user_credentials():
    gemini_key = st.text_input("Enter your Gemini API Key:", type="password")
    if gemini_key:
        if gemini_key == password_for_gemini_key:
            gemini_key = os.getenv('GEMINI_KEY')
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
    
    file_path = st.text_input("Enter the PDF file path:")
    file_path = file_path.strip().strip('"').strip("'")
    return gemini_key, file_path

gemini_key, file_path = get_user_credentials()

if not gemini_key:
    st.warning("Please enter your Gemini API Key")
    st.stop()

if not file_path:
    st.warning("Please enter the PDF file path")
    st.stop()

loc = file_path

keywords = st.text_input("Enter what words you wanna have followed by comma:")
keywords = keywords.split(",")
st.write(keywords)

mainList = []

page_input = st.text_input("Enter what page you want to start, followed by a comma, what page you want to end:")
if not page_input:
    st.write("Please enter valid page range (e.g., 1,5)")
    st.stop()

page = page_input.split(",")
if len(page) != 2 or not page[0].strip() or not page[1].strip():
    st.write("Please enter valid page range (e.g., 1,5)")
    st.stop()
else:
    try:
        if int(page[0]) <= 0 or int(page[1]) <= 0:
            st.write("Try Again, incorrect values or format")
        else:
            if page_input:
                st.session_state['page_range'] = page_input
                st.session_state['starting_page'] = int(page[0])
                st.session_state['ending_page'] = int(page[1])
            
            starting_page = st.session_state.get('starting_page')
            ending_page = st.session_state.get('ending_page')

            if st.button("Load Preview"):
                if 'preview_data' not in st.session_state:
                    with reader.open(loc) as pdf:
                        page_obj = pdf.pages[starting_page-1]
                        data = page_obj.extract_table()
                        for entrie in data:
                            rowList = []
                            for line in entrie:
                                line = str(line).replace("\n",", ")
                                rowList.append(line)
                            mainList.append(rowList)
                        st.session_state['preview_data'] = mainList
                        st.session_state['table_data'] = data

            if 'preview_data' in st.session_state:
                for entrie in st.session_state['preview_data']:
                    st.write(entrie)
                st.write("")
                st.write("")

                starting_entrie = st.number_input("Based on this preview, which entrie would you like to start with?", min_value=1, value=1)
                ending_entrie = st.number_input("Based on this preview, which entrie would you like to end with. If no preference please enter 0", min_value=0, value=0)

                if ending_entrie != 0 and ending_entrie < starting_entrie:
                    st.write("invalid. Starting number must be less than ending number and ending number must fit between domain of data")
                elif ending_entrie > len(st.session_state.get('table_data', [])):
                    st.write("invalid. Starting number must be less than ending number and ending number must fit between domain of data")
                else:
                    if st.button("Process Companies") or "PROCESSED" in st.session_state:
                        if "PROCESSED" not in st.session_state:
                            st.session_state['PROCESSED'] = True
                            mainList = []
                            with reader.open(loc) as pdf:
                                for page_obj in pdf.pages[starting_page-1:ending_page-1]:
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
                                if "gemini_output" not in st.session_state:
                                    gemini_output, TimedOut = analyseDataGeminiWeb("Here is a company entry, based on this entry Find where the CompanyName, Address, Phone number, Linkedid, and Website are located. I might give you more than 5 or less than 5 entries. Return a 1D JSON format array with the number corresponding to place where that information is found in the entrie: Example if Phone number is on 6 column in the raw data, then return 5 in 4th index of array. Start at 0. If any of these info is not found return -1 for that entrie. Your ouput hould only be that array no talking", mainList[0], gemini_key)
                                    if not TimedOut:
                                        order_array = text_cleaner(gemini_output.text)
                                        st.session_state['order_array'] = order_array
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
                                    order_array = st.session_state['order_array']
                                    mainList = st.session_state['mainList']
                            else:
                                st.write("No companies found")
                        
            if 'Data_organized' not in st.session_state and 'order_array' in st.session_state:
                if st.session_state.get('order_array'):
                    order_array = st.session_state['order_array']
                    mainList = st.session_state['mainList']
                    
                    print("!EN")
                    data_check = st.text_input("MAPS API Please:", type="password")
                    print(data_check)
                    if data_check:
                        if not 'maps_key_validated' in st.session_state:
                            print("ENTERED")
                            if data_check == password_for_gemini_key:
                                maps_api_key = os.getenv('MAPS_KEY')
                                re_ordered_array = orderganizeData(order_array, mainList, maps_api_key)
                                st.session_state['Data_organized'] = re_ordered_array
                                st.session_state['maps_key_validated'] = True
                            else:
                                try:
                                    maps_access = googlemaps.Client(data_check)
                                    st.write("Key is valid!")
                                    re_ordered_array = orderganizeData(order_array, mainList, data_check)
                                    st.session_state['Data_organized'] = re_ordered_array
                                    st.session_state['maps_key_validated'] = True
                                except Exception as e:
                                    st.write("Key is invalid or error occurred, Maps integration will not work. Alt to DDGS")
                                    re_ordered_array = orderganizeData(order_array, mainList, "DDGS")
                                    st.session_state['Data_organized'] = re_ordered_array
                                    st.session_state['maps_key_validated'] = True
                                    print("HERE")
            if 'Data_organized' in st.session_state:
                if 'password_entered' not in st.session_state:
                    final = st.session_state['Data_organized']
                    st.write("")
                    st.write("")
                    st.write(final)
                    data_check = st.text_input("Enter DSQ Password:", type="password")
                    if data_check:
                        if data_check == password_for_gemini_key:
                            st.write("Good")
                            st.session_state['password_entered'] = True
                            st.session_state['old_data'] = []
                            with open("data.json", "r") as file:
                                st.session_state['old_data'] = json.load(file)
                        else:
                            st.write("Password incorrect data not assecible")
                
                if st.session_state['password_entered']:
                    if 'augment_action' not in st.session_state:
                        old_data = st.session_state.get('old_data', [])
                        final = st.session_state['Data_organized']
                        print(final)
                        print(old_data)
                        augment = st.text_input("do you 'Update' or 'Clear' old data:")
                        if augment:
                            st.session_state['augment_action'] = augment
                    
                    if st.session_state['augment_action']:
                        if 'json_saved' not in st.session_state:
                            augment = st.session_state['augment_action']
                            final = st.session_state['Data_organized']
                            old_data = st.session_state.get('old_data', [])
                            
                            if augment == "Update":
                                first_elements_current_list = {row[0].lower() for row in final}
                                print(first_elements_current_list)
                                for i in range(len(old_data)):
                                    if old_data[i][0].lower() not in first_elements_current_list:
                                        final.append(old_data[i])
                                st.write("Data retrieve and updated with new info")
                            else:
                                st.write("Data cleared")
                            with open("data.json", "w") as file:
                                json.dump(final, file, indent=4)
                            st.session_state['json_saved'] = True
                        
                        st.write("")
                        st.write("")
                        data = framework.DataFrame(st.session_state['Data_organized'])
                        st.table(data)
                        st.write("Succesfulley updated JSON")

    except ValueError:
        st.write("Please enter valid numbers for pages")