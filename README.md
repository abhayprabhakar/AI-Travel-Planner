# AI Travel Planner  

**AI Travel Planner** is a web-based application designed to help users plan personalized travel itineraries. By providing details like the origin, destination, and travel preferences, users receive a custom travel plan that includes flight options, accommodation recommendations, and suggested activities. The application integrates **SerpApi** for real-time flight and accommodation data and utilizes **AI-powered language models (LLMs)** for itinerary generation and travel insights.

### **Key Features:**  
- **Personalized Itinerary Generation:** Users can input travel queries, and the system generates a detailed, day-wise itinerary, including flights, accommodations, and activities.
- **Flight Search:** The application uses **SerpApi** to fetch flight information based on the user's origin, destination, and travel dates, providing options for available flights.
- **Accommodation Recommendations:** Using **SerpApi**, the planner fetches real-time information about hotels, lodges, and resorts near the destination, tailored to the user's preferences.
- **AI-Powered Recommendations:** The system leverages **LLMs** (such as Groq API) to suggest activities, sightseeing spots, and other personalized recommendations based on user preferences.
- **Responsive Web Interface:** Built with **HTML**, **CSS**, **JavaScript**, and **Bootstrap**, the application provides a user-friendly, mobile-responsive interface.
- **Backend Powered by Flask:** The backend, built using **Python** and **Flask**, integrates with **SerpApi** and **LLMs** to provide seamless travel planning.

### **Technologies Used:**  
- **Frontend:** HTML, CSS, JavaScript, Bootstrap  
- **Backend:** Python (Flask)  
- **APIs:**  
   - **SerpApi** (Flight and Accommodation Data)  
   - **Groq API** (AI-Powered Text Generation for Itinerary Creation)  
- **Database:** SQLite/PostgreSQL for storing airport and accommodation information  
- **Libraries:** Pandas, Requests, Marked.js  

### **How It Works:**  
1. **User Input:** Users provide their travel query (e.g., “Plan a trip from New York to Paris for 5 days starting Jan 1”).
2. **Data Retrieval:** The backend queries **SerpApi** for relevant flight and accommodation data based on the user's input.
3. **AI-Powered Itinerary Generation:** Using the retrieved data, an **AI model** generates a personalized itinerary for the user, including flight details, accommodation suggestions, and recommendations for activities.
4. **Results Display:** The generated itinerary is displayed on the frontend, where users can review and finalize their travel plans.

### **Future Enhancements:**  
- Real-time price tracking for flights and accommodations  
- User account creation to save preferences and itineraries  
- Multi-language support for a broader audience  
- Integration with payment gateways for booking  
- Weather updates for the destination  
