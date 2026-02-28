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
    if gemini_key == password_for_gemini_key:
        gemini_key = os.getenv('GEMINI_KEY')
    try:
        client = genai.Client(api_key=gemini_key)
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents='Say hello'
        )
        st.write("Key is valid!")
    except Exception as e:
        st.write("Key is invalid or error occurred, Gemini integration will not work")
    file_path = st.text_input("Enter the PDF file path:")
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

page = st.text_input("Enter what page you want to start, followed by a comma, what page you want to end:").split(",")
if len(page) != 2 or not page[0].strip() or not page[1].strip():
    st.write("Please enter valid page range (e.g., 1,5)")
else:
    try:
        if int(page[0]) <= 0 or int(page[1]) <= 0:
            st.write("Try Again, incorrect values or format")
        else:
            starting_page = int(page[0])
            ending_page = int(page[1])

            if st.button("Load Preview"):
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

                        st.write(mainList)
                        st.write("")
                        st.write("")

                        final = []
                        if len(mainList) > 0:
                            gemini_output, TimedOut = analyseDataGeminiWeb("Here is a company entry, based on this entry Find where the CompanyName, Address, Phone number, Linkedid, and Website are located. I might give you more than 5 or less than 5 entries. Return a 1D JSON format array with the number corresponding to place where that information is found in the entrie: Example if Phone number is on 6 column in the raw data, then return 5 in 4th index of array. Start at 0. If any of these info is not found return -1 for that entrie. Your ouput hould only be that array no talking", mainList[0], gemini_key)
                            if not TimedOut:
                                order_array = text_cleaner(gemini_output.text)
                                str = ""
                                if order_array[0] != -1:
                                    str += "Company found, "
                                if order_array[1] != -1:
                                    str += "Address found, "
                                if order_array[2] != -1:
                                    str += "Phone Number found, "
                                if order_array[3] != -1:
                                    str += "LinkedIn found, "
                                if order_array[4] != -1:
                                    str += "Company Website found"
                                st.write(str)
                                re_ordered_array = []
                                print("!EN")
                                data_check = st.text_input("MAPS API Please:", type="password")
                                print(data_check)
                                if not "API ADDED" in st.session_state or st.session_state['API ADDED'] == False:
                                    if data_check:
                                        print("ENTERED")
                                        if data_check == password_for_gemini_key:
                                            maps_api_key = os.getenv('MAPS_KEY')
                                            re_ordered_array = orderganizeData(order_array, mainList,maps_api_key)
                                            final = re_ordered_array
                                            st.session_state['Data_organized'] = final
                                            st.session_state['API ADDED'] = True
                                        else:
                                            try:
                                                maps_access = googlemaps.Client(data_check)
                                                st.write("Key is valid!")
                                                re_ordered_array = orderganizeData(order_array, mainList,data_check)
                                                final = re_ordered_array
                                                st.session_state['API ADDED'] = True
                                                value = True
                                            except Exception as e:
                                                st.write("Key is invalid or error occurred, Maps integration will not work. Alt to DDGS")
                                                re_ordered_array = orderganizeData(order_array, mainList,"DDGS")
                                                st.session_state['API ADDED'] = False
                        else:
                            st.write("No companies found")
            if 'Data_organized' in st.session_state:
                final = st.session_state['Data_organized']
                st.write("")
                st.write("")
                st.write(final)
                data_check = st.text_input("Enter DSQ Password:", type="password")
                if data_check:
                    if data_check == password_for_gemini_key:
                        st.write("Good")
                        old_data = []
                        with open("data.json", "r") as file:
                            old_data = json.load(file)
                        print(final)
                        print(old_data)
                        augment = st.text_input("do you 'Update' or 'Clear' old data:")
                        if augment:
                            if augment == "Update":
                                first_elements_current_list = {row[0].lower() for row in final}
                                print(first_elements_current_list)
                                for i in range(len(old_data)):
                                    if old_data[i][0] not in first_elements_current_list:
                                        final.append(old_data[i])
                                st.write("Data retrieve and updated with new info")
                            else:
                                st.write("Data cleared")
                            with open("data.json", "w") as file:
                                json.dump(final, file, indent=4)
                        st.write("")
                        st.write("")
                        if augment:
                            data = framework.DataFrame(final)
                            st.table(data)
                            st.write("Succesfulley updated JSON")
                    else:
                        st.write("Password incorrect data not assecible")

    except ValueError:
        st.write("Please enter valid numbers for pages")