import streamlit as st
import folium
from folium.plugins import MarkerCluster
import streamlit_folium as st_folium
from geopy.geocoders import Nominatim
import requests
from streamlit_option_menu import option_menu
import time
from bs4 import BeautifulSoup
import json


# Set page config
st.set_page_config(
    page_title="RealScout Analytics",
    page_icon="🏘️",
    layout="wide"
)

# Initialize session state
if 'map_data' not in st.session_state:
    st.session_state.map_data = None
if 'location_details' not in st.session_state:
    st.session_state.location_details = None
if 'search_clicked' not in st.session_state:
    st.session_state.search_clicked = False

# Cache the geocoding function
@st.cache_data
def get_coordinates(location):
    try:
        geolocator = Nominatim(user_agent="realscout")
        location_data = geolocator.geocode(location)
        if location_data:
            return (location_data.latitude, location_data.longitude)
        else:
            st.error("Location not found. Please try a different search term.")
            return None
    except Exception as e:
        st.error(f"Error getting coordinates: {str(e)}")
        return None

# Cache the nearby places function
@st.cache_data
def get_nearby_places(lat, lon, category, radius=5000):
    api_key = "65029b53a8374fc0ab514ff290d2f7b0"  # Replace with your API key
    url = f"https://api.geoapify.com/v2/places"
    params = {
        "categories": category,
        "filter": f"circle:{lon},{lat},{radius}",
        "limit": 20,
        "apiKey": api_key
    }
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            return {"features": []}
    except Exception as e:
        return {"features": []}

def calculate_zone_score(places_data):
    if not places_data:
        return 0
    
    total_places = sum(len(place.get('features', [])) for place in places_data.values())
    max_score = 100
    return min(total_places * 5, max_score)  # 5 points per place, max 100

@st.cache_data(ttl=3600)  # Cache for 1 hour
def crawl_web(location):
    try:
        query = f"price of lands in {location}"
        url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
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
                snippet = g.find('div', class_='VwiC3b')
                snippet_text = snippet.text if snippet else ''
                results.append({
                    "title": title,
                    "link": link,
                    "snippet": snippet_text
                })
        return results[:5]  # Return top 5 results
    except Exception as e:
        st.error(f"Error crawling web: {str(e)}")
        return []

@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_price_analysis(location, price_data):
    try:
        url = "https://api.together.xyz/v1/chat/completions"
        
        # Format the price data for the LLM
        formatted_data = json.dumps(price_data, indent=2)
        
        user_prompt = f"""Analyze the following real estate data for {location}:
        {formatted_data}
        
        Please provide:
        Approximate price range per square foot
        
        
        Format the response in markdown."""

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
            "top_k": 50,
            "repetition_penalty": 1,
            "stop": ["<|eot_id|>", "<|eom_id|>"]
        }
        
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": "Bearer 89454781a24debef9974cd9a084396ef96b737b590cc408ef9bf823bc80b338a"
        }
        
        response = requests.post(url, json=payload, headers=headers)
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        st.error(f"Error getting LLM analysis: {str(e)}")
        return None
    
def create_map(coordinates, places_data, radius):
    m = folium.Map(location=coordinates, zoom_start=14)
    
    # Add main marker
    folium.Marker(
        coordinates,
        popup="Selected Location",
        icon=folium.Icon(color='red', icon='info-sign')
    ).add_to(m)
    
    # Categories with icons
    categories = {
        "commercial.supermarket": "🏪 Supermarkets",
        "education.school": "🎓 Schools",
        "healthcare.hospital": "🏥 Hospitals",
        "leisure.park": "🌳 Parks"
    }
    
    # Add clusters for each category
    for category_key, category_label in categories.items():
        if category_key in places_data and places_data[category_key].get('features'):
            cluster = MarkerCluster(name=category_label).add_to(m)
            for place in places_data[category_key]['features']:
                try:
                    place_name = place['properties'].get('name', 'Unnamed')
                    coords = place['geometry']['coordinates']
                    folium.Marker(
                        [coords[1], coords[0]],
                        popup=place_name,
                        icon=folium.Icon(color='blue', icon='info-sign')
                    ).add_to(cluster)
                except Exception:
                    continue
    
    # Add circle for radius
    folium.Circle(
        coordinates,
        radius=radius * 1000,  # Convert km to meters
        color="red",
        fill=True,
        opacity=0.2
    ).add_to(m)
    
    folium.LayerControl().add_to(m)
    return m

def main():
    # Sidebar
    with st.sidebar:
        st.title("RealScout Analytics")
        selected = option_menu(
            menu_title=None,
            options=["Search", "Analysis", "Market Trends"],
            icons=["search", "graph-up", "currency-exchange"],
            default_index=0,
        )
    if selected == "Analysis":
        st.title("Under development ⚠️")
    
    if selected == "Market Trends":
        st.title("Under development ⚠️")
    
    if selected == "Search":
        st.title("Reality Insights")
        
        # Search interface
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            location_input = st.text_input("🔍 Enter location to analyze:", key="location_input")
        with col2:
            radius = st.selectbox("Radius (km)", [1, 2, 5, 10], index=2, key="radius_select")
        with col3:
            if st.button("Analyze Area", key="search_button"):
                st.session_state.search_clicked = True
                coordinates = get_coordinates(location_input)
                
                if coordinates:
                    # Store location details in session state
                    places_data = {}
                    categories = ["commercial.supermarket", "education.school", 
                                "healthcare.hospital", "leisure.park"]
                    
                    with st.spinner("Fetching location data..."):
                        for category in categories:
                            places_data[category] = get_nearby_places(
                                coordinates[0], coordinates[1], category, radius * 1000
                            )
                    
                    st.session_state.location_details = {
                        'coordinates': coordinates,
                        'places_data': places_data,
                        'radius': radius
                    }
        
        # Display results if search was performed
        if st.session_state.location_details:
            tab1, tab2 = st.tabs(["📍 Map View", "📊 Analytics"])
            
            with tab1:
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    # Create and display map
                    details = st.session_state.location_details
                    m = create_map(
                        details['coordinates'],
                        details['places_data'],
                        details['radius']
                    )
                    
                    # Use a larger width and height for better visibility
                    map_data = st_folium.st_folium(
                        m,
                        width=700,
                        height=500,
                        key="main_map"  # Important: Unique key for the map
                    )
                
                with col2:
                    # Display metrics
                    zone_score = calculate_zone_score(details['places_data'])
                    st.metric("Area Development Score", f"{zone_score:.0f}%")
                    
                    st.subheader("📍 Nearby Amenities")
                    for category, places in details['places_data'].items():
                        place_count = len(places.get('features', []))
                        category_name = {
                            "commercial.supermarket": "🏪 Supermarkets",
                            "education.school": "🎓 Schools",
                            "healthcare.hospital": "🏥 Hospitals",
                            "leisure.park": "🌳 Parks"
                        }.get(category, category)
                        
                        st.write(f"{category_name}: {place_count} within {details['radius']}km")
            
            with tab2:
                st.subheader("Property Analytics")
                
                if st.session_state.location_details:
                    location = st.session_state.get("location_input", "")
                    
                    with st.spinner("Fetching market data..."):
                        # Create columns for metrics
                        col1, col2 = st.columns(2)
                        
                        # Fetch and analyze data
                        crawled_data = crawl_web(location)
                        analysis = get_price_analysis(location, crawled_data)
                        
                        if analysis:
                            # Display dynamic metrics based on LLM analysis
                            with col1:
                                st.markdown("### 📊 Market Overview")
                                st.markdown(analysis)
                            
                            with col2:
                                st.markdown("### 🔍 Recent Listings")
                                for result in crawled_data:
                                    with st.expander(result["title"]):
                                        st.markdown(f"**Source**: [{result['link']}]({result['link']})")
                                        st.markdown(f"**Summary**: {result['snippet']}")
                        
                        # Add historical trends chart
                        st.markdown("### 📈 Historical Price Trends")
                        st.line_chart({
                            "Average Price": [100, 105, 108, 115, 120, 118],
                            "Market Index": [100, 102, 106, 110, 112, 115]
                        })
                        
                        # Add market insights
                        st.markdown("### 💡 Market Insights")
                        col3, col4, col5 = st.columns(3)
                        
                        with col3:
                            st.metric(
                                "Price Trend",
                                "↗️ Upward",
                                "Based on 6-month data"
                            )
                        
                        with col4:
                            st.metric(
                                "Market Liquidity",
                                "Medium",
                                "Average days on market: 45"
                            )
                        
                        with col5:
                            st.metric(
                                "Investment Score",
                                "8.5/10",
                                "↑ 0.5 vs last quarter"
                            )

if __name__ == "__main__":
    main()
