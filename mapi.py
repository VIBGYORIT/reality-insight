import json
import streamlit as st
import folium
from folium.plugins import MarkerCluster
import streamlit_folium as st_folium
from geopy.geocoders import Nominatim
import requests
from bs4 import BeautifulSoup

def get_coordinates(location):
    geolocator = Nominatim(user_agent="mapi")
    location = geolocator.geocode(location)
    if location:
        return (location.latitude, location.longitude)
    else:
        return None

def get_nearby_places(lat, lon, category):
    print("nearby places is called")
    url = f"https://api.geoapify.com/v2/places?categories={category}&filter=circle:{lon},{lat},5000&limit=20&apiKey=65029b53a8374fc0ab514ff290d2f7b0"
    response = requests.get(url)
    return response.json()

def crawl_web(location):
    query = f"price of lands in {location}"
    url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Extract relevant information from the search results
    results = []
    for g in soup.find_all('div', class_='g'):
        anchors = g.find_all('a')
        if anchors:
            link = anchors[0]['href']
            title = g.find('h3')
            if title:
                title = title.text
            else:
                title = 'No title'
            item = f"- [{title}]({link})"
            results.append(item)
    
    return "\n".join(results[:5])  # Return top 5 results

def get_price_with_LLM(price_data):
    url = "https://api.together.xyz/v1/chat/completions"
    user_prompt="```"+price_data+"``` \n Process the data given to u and give me the approximate price of the real estate, give me the reference link(FULL LINK) from which you are pointing the values"
    payload = {
        "messages": [
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        "model": "meta-llama/Llama-Vision-Free",
        "temperature": 0.7,
        "top_p": 0.7,
        "stream": False,
        "top_k":50,
        "repetition_penalty":1,
        "stop":["<|eot_id|>","<|eom_id|>"],
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": "Bearer 89454781a24debef9974cd9a084396ef96b737b590cc408ef9bf823bc80b338a"
    }

    response = requests.post(url, json=payload, headers=headers)
    return response

st.title("Interactive Map Viewer with Nearby Places and Land Price Info")

location_input = st.text_input("Enter a location:")

if location_input:
    coordinates = get_coordinates(location_input)
    if coordinates:
        st.write(f"Map for {location_input}")
        
        my_map = folium.Map(location=coordinates, zoom_start=13, control_scale=True)

        # Add marker for the searched location
        folium.Marker(coordinates, popup=location_input, icon=folium.Icon(color='red', icon='info-sign')).add_to(my_map)

        # Create marker clusters for each category
        categories = {
            "commercial.supermarket": "Supermarkets",
            "healthcare.hospital": "Hospital",
            "education": "Educational Institutes",
            "catering": "Food and Catering"
        }

        for category, display_name in categories.items():
            places = get_nearby_places(coordinates[0], coordinates[1], category)
            if places['features']:
                cluster = MarkerCluster(name=display_name).add_to(my_map)
                for place in places['features']:
                    place_name = place['properties'].get('name', 'Unnamed')
                    place_lat = place['geometry']['coordinates'][1]
                    place_lon = place['geometry']['coordinates'][0]
                    folium.Marker(
                        [place_lat, place_lon],
                        popup=place_name,
                        icon=folium.Icon(color='blue', icon='info-sign')
                    ).add_to(cluster)

        # Add layer control to toggle marker clusters
        folium.LayerControl().add_to(my_map)

        st_data = st_folium.st_folium(my_map, width=725, height=500)

        # Display information about nearby places
        st.subheader("Nearby Places")
        
        # Create a 2x2 grid for categories
        col1, col2 = st.columns(2)
        cols = [col1, col2, col1, col2]
        
        for i, (category, display_name) in enumerate(categories.items()):
            with cols[i]:
                st.write(f"### {display_name}")
                places = get_nearby_places(coordinates[0], coordinates[1], category)
                if places['features']:
                    for place in places['features'][:3]:  # Display top 3 places
                        place_name = place['properties'].get('name', 'Unnamed')
                        place_address = place['properties'].get('formatted', 'Address not available')
                        st.write(f"- **{place_name}**")
                        st.write(f"  Address: {place_address}")
                else:
                    st.write(f"No {display_name.lower()} found nearby.")

        # Web crawling for land price information
        st.subheader("Land Price Information")
        if st.button("Get Land Price Information"):
            with st.spinner("Fetching land price information..."):
                land_price_crawled_info = crawl_web(location_input)
                land_price = get_price_with_LLM(land_price_crawled_info)
                response_json = json.loads(land_price.text)
                content = response_json['choices'][0]['message']['content']
                st.markdown(content)

    else:
        st.write("Location not found. Please enter a valid location.")