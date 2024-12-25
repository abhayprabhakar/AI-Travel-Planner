from flask import Flask, request, jsonify, render_template
import os
from dotenv import load_dotenv
from serpapi import GoogleSearch
from groq import Groq
import json
from datetime import datetime
from flask_cors import CORS
import csv
from fuzzywuzzy import process
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import re
from datetime import date,timedelta
from io import BytesIO
from PIL import Image
import requests
import base64
import uuid

today = date.today() + timedelta(7)

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SERPAPI_API_KEY = os.getenv("SERPAPI_API")

app = Flask(__name__)
CORS(app)

client = Groq(api_key=GROQ_API_KEY)

def ask_llm(prompt):
    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7, 
            top_p=1,
            stream=False
        )
        if hasattr(completion.choices[0].message, 'content'):
            return completion.choices[0].message.content
        else:
            return "Error: No content found in the response."

    except Exception as e:
        return f"Error: {str(e)}"
    
airports_data = {}
def load_airports(filepath="data/airports.csv"):
    global airports_data
    try:
        with open(filepath, 'r', encoding='utf-8', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                city = row.get("City", "").strip().lower()
                iata = row.get("IATA_Code", "").strip().upper()
                if city and iata and iata != "N/A" and iata != "":
                    airports_data[city] = iata
                    airports_data[iata] = iata  
        print("Airports data loaded from file.")
        return True
    except FileNotFoundError:
        print(f"Warning: Airport file '{filepath}' not found.")
        return False
    except Exception as e:
        print(f"Error reading airport file: {e}")
        return False

airports_loaded = load_airports()

def get_iata_code(location):
    if not location:
        return None
        
    location = location.strip().lower()
    if airports_loaded:
        if location in airports_data:
            return airports_data[location]
        elif location.upper() in airports_data:
            return airports_data[location.upper()]
        else:
            best_match, score = process.extractOne(location, airports_data.keys())
            if score > 80:
                return airports_data[best_match]
    return None

def parse_llm_response(response):
    try:
        if '{' in response and '}' in response:
            json_str = response[response.find('{'):response.rfind('}')+1]
            return json.loads(json_str)

        lines = response.split('\n')
        result = {
            'intent': '',
            'origin': '',
            'destination': '',
            'date': '',
            'duration': '7'  
        }

        for line in lines:
            line = line.strip('- ').lower()
            if 'intent' in line:
                result['intent'] = line.split(':')[-1].strip()
            if 'origin' in line:
                result['origin'] = line.split(':')[-1].strip()
            elif 'destination' in line:
                result['destination'] = line.split(':')[-1].strip()
            elif 'date' in line:
                try:
                    date_str = line.split(':')[-1].strip()
                    for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%m-%d-%Y', '%d-%m-%Y'):
                        try:
                            date_obj = datetime.strptime(date_str, fmt)
                            result['date'] = date_obj.strftime("%Y-%m-%d")
                            break
                        except ValueError:
                            continue
                    else:
                        result['date'] = today
                except ValueError:
                    print("Error parsing date")
            elif 'duration' in line:
                duration_str = line.split(':')[-1].strip()
                duration_digits = ''.join(filter(str.isdigit, duration_str))
                if duration_digits:
                    result['duration'] = int(duration_digits)
        
        print(result)
        return result
    except Exception as e:
        print(f"Error in parse_llm_response: {e}")
        return None

def search_flights(origin_location, destination_location, date, adults=1):
    if not origin_location or not destination_location:
        print("Origin or destination is missing. Cannot perform flight search.")
        return {"flights": [], "error": "Missing origin or destination"}

    origin_iata = get_iata_code(origin_location)
    destination_iata = get_iata_code(destination_location)

    if not origin_iata:
        print(f"Could not find IATA code for origin: {origin_location}")
        return {"flights": [], "error": f"No IATA code found for origin: {origin_location}"}

    if not destination_iata:
        print(f"Could not find IATA code for destination: {destination_location}")
        return {"flights": [], "error": f"No IATA code found for destination: {destination_location}"}

    print(f"Searching flights from {origin_iata} to {destination_iata}")
    
    params = {
        "api_key": SERPAPI_API_KEY,
        "engine": "google_flights",
        "hl": "en",
        "gl": "in",
        "departure_id": origin_iata,
        "arrival_id": destination_iata,
        "outbound_date": date,
        "currency": "INR",
        "type": "2"

    }
    print(params)
    try:
        search = GoogleSearch(params)
        results = search.get_dict()
        flight_data = {
            "best_flights": [],
            "airports": [],
            "price_insights": {}
        }

        if results.get("best_flights"):
            flight_data["best_flights"] = results["best_flights"][:3]  # Get only the top 3

        if results.get("airports"):
            flight_data["airports"] = results["airports"]

        if results.get("price_insights"):
            price_insights = results["price_insights"].copy()
            if "price_history" in price_insights:
                del price_insights["price_history"] 
            flight_data["price_insights"] = price_insights
        return flight_data
    except Exception as e:
        print(f"Error searching flights: {e}")
        return {"flights": []}



def search_places(destination):
    places_data = {}
    for place_type, search_type in [("attractions", "tourist_attraction"), ("hotels", "lodging"), ("restaurants", "restaurant")]:
        params = {
            "api_key": SERPAPI_API_KEY,
            "engine": "google_local",
            "google_domain": "google.com",
            "q": f"top {place_type} in {destination}",
            "type": search_type
        }
        search = GoogleSearch(params)
        results = search.get_dict()
        places_data[place_type] = []
        if results.get("local_results"):
            for place in results.get("local_results", []):
                try:
                    places_data[place_type].append({
                        "title": place.get("title", ""),
                        "website": place.get("website", ""),
                        "address": place.get("address", ""),
                        "phone": place.get("phone", ""),
                        "rating": place.get("rating", ""),
                        "reviews": place.get("reviews", ""),
                        "thumbnail": place.get("thumbnail", "")
                    })
                except (AttributeError, TypeError, KeyError):
                    print(f"Error parsing {place_type} data: {place}")
                    continue
    return places_data



def create_itinerary(places_data, duration_days):
    prompt = f"""
    Create a {duration_days}-day travel itinerary using these places:
    Attractions: {', '.join([f"{place.get('title', '')} ({place.get('website', '')})" for place in places_data['attractions'][:10]])}
    Hotels: {', '.join([f"{place.get('title', '')} ({place.get('website', '')})" for place in places_data['hotels'][:5]])}
    Restaurants: {', '.join([f"{place.get('title', '')} ({place.get('website', '')})" for place in places_data['restaurants'][:10]])}
    Output as markdown format.
    """
    return ask_llm(prompt)

def get_place_images(place_name):
    params = {
        "api_key": SERPAPI_API_KEY,  
        "engine": "google_images",
        "google_domain": "google.com",
        "q": f"{place_name} place image",  
        "hl": "en",
        "gl": "us"
    }

    try:
        search = GoogleSearch(params)
        results = search.get_dict()
        images = []
        if results.get("images_results"):
            for image in results["images_results"]:
                original_image_url = image.get("original")  
                if original_image_url: 
                    images.append(original_image_url)
        print(images)
        return images
    except Exception as e:
        print(f"Error fetching images for {place_name}: {e}")
        return [] 

def resize_image(image_url, width, height):
    try:
        response = requests.get(image_url, stream=True)
        response.raise_for_status()  

        image = Image.open(BytesIO(response.content))
        image = image.resize((width, height), Image.LANCZOS) 
        buffered = BytesIO()
        image.save(buffered, format="JPEG")  
        return f"data:image/jpeg;base64,{base64.b64encode(buffered.getvalue()).decode()}" #Return base64 encoded image
    except requests.exceptions.RequestException as e:
        print(f"Error downloading image: {e}")
        return None
    except OSError as e: 
        print(f"Error processing image format: {e}")
        return None
    except Exception as e:
        print(f"Error resizing image: {e}")
        return None

def get_flight_recommendations(flights_data):
    if not flights_data or not flights_data.get("best_flights"):
        return "No flight data available."

    flights = flights_data["best_flights"]
    num_flights = len(flights)

    if num_flights == 0:
        return "No flights found for this route."

    recommendation = "Here are the top {} flight options:\n".format(num_flights)

    for i, flight in enumerate(flights):
        departure_airport = flight["flights"][0]["departure_airport"]["name"]
        arrival_airport = flight["flights"][0]["arrival_airport"]["name"]
        departure_time = flight["flights"][0]["departure_airport"]["time"]
        arrival_time = flight["flights"][0]["arrival_airport"]["time"]
        airline = flight["flights"][0]["airline"]
        price = flight.get("price", "Price not available")  
        duration = flight["flights"][0]["duration"]
        recommendation += f"\nFlight {i+1}:\n"
        recommendation += f"- Airline: {airline}\n"
        recommendation += f"- From: {departure_airport} ({departure_time})\n"
        recommendation += f"- To: {arrival_airport} ({arrival_time})\n"
        recommendation += f"- Duration: {duration} minutes\n"
        recommendation += f"- Price: {price}\n\n"
    print(recommendation)
    return recommendation

def get_travel_recommendations(flights_data, places_data, duration_days):
    flight_recommendations = get_flight_recommendations(flights_data)

    markdown_text = f"""
    Analyze this travel data and provide recommendations (mentioning all available flight recommendations with prices and websites if available):

    **Flights:**
    {flight_recommendations}

    """
    image_placeholders = {}
    for place_type, places in places_data.items():
        markdown_text += f"\n\n**{place_type.capitalize()}:**\n"
        for i, place in enumerate(places[:3]):  # Limit to top 3 places
            place_name = place.get("title", "")
            website = place.get("website", "")
            if place_name:
                """ images = get_place_images(place_name)
                image_url = images[0] if images else ""  # Use the first image or an empty string
                print("\nimage url: "+image_url+"\n\n") """
                markdown_text += f"\n{i+1}. **{place_name}**"
                if website:
                    markdown_text += f" ([Website]({website}))\n" 
                else:
                    markdown_text += "\n"
                """ if image_url:
                    resized_image = resize_image(image_url, 500, 300)
                    if resized_image:
                        unique_placeholder = str(uuid.uuid4())  # Generate a unique string
                        image_placeholders[unique_placeholder] = [resized_image, place_name]  # Store it
                        markdown_text += f"\"this is placeholder for image so let it be as it is don't change\"{unique_placeholder}\n"  # Use placeholder in Markdown
                    else:
                        markdown_text += "Error resizing image.\n" """
    markdown_text += "\nOutput as markdown format."
    llm_response = ask_llm(markdown_text)
    
    """ for placeholder, base64_image in image_placeholders.items():
        llm_response = llm_response.replace(placeholder, f"<br>![{base64_image[1]}]({base64_image[0]})<br>") """
    return llm_response

@app.route('/travel', methods=['POST'])
def travel_planner():
    try:
        data = request.json
        query = data['query']
        prompt = f"Extract travel intent, origin, destination, date, and duration (in days) from query IF THERE IS NO DATE MENTIOND THEN USE THE GIVEN DATE HERE '{today}': {query}"
        llm_response = ask_llm(prompt)

        if "Error" in llm_response:
            return jsonify({"error": llm_response}), 500

        details = parse_llm_response(llm_response)
        print("Extracted Details:", details)

        origin = details.get('origin', '')
        destination = details.get('destination', '')
        date = details.get('date', '')
        duration = details.get('duration', '7')

        flights_data = search_flights(origin, destination, date)
        
        if flights_data.get("error"):
            return jsonify({"error": flights_data["error"]}), 400
            
        places_data = search_places(destination)
        itinerary = create_itinerary(places_data, int(duration))
        recommendations = get_travel_recommendations(flights_data, places_data, int(duration))

        travel_plan = {
            "itinerary": itinerary,
            "recommendations": recommendations,
            "flights": flights_data
        }

        return jsonify(travel_plan)

    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"}), 500
    
@app.route('/')
def home():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)