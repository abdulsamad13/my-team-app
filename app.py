

import streamlit as st
import pandas as pd
import pytesseract
from PIL import Image
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from datetime import date
import json
import os

st.set_page_config(
    page_title="Umrah Business Manager",
    page_icon="🕋",
    layout="wide"
)

DATA_FILE = "umrah_rates.json"

DEFAULT_RATES = {
    "hotels": [
        {"city": "Makkah", "hotel": "Qasr Al Sharq Tower",
         "quad": 8, "triple": 10, "double": 15, "currency": "SAR"},
        {"city": "Makkah", "hotel": "Mayar Mayser",
         "quad": 9, "triple": 12, "double": 18, "currency": "SAR"},
        {"city": "Madinah", "hotel": "Retaj Al Madina",
         "quad": 30, "triple": 40, "double": 60, "currency": "SAR"},
        {"city": "Madinah", "hotel": "Rabwa Safwa 7",
         "quad": 25, "triple": 32, "double": 47, "currency": "SAR"},
    ],
    "transport": [
        {"name": "Sedan / 4 Seater", "rate": 220, "currency": "SAR"},
        {"name": "Starex / 7 Seater", "rate": 260, "currency": "SAR"},
        {"name": "Mini Bus / 9 Seater", "rate": 330, "currency": "SAR"},
        {"name": "Coaster / 20 Seater", "rate": 530, "currency": "SAR"},
        {"name": "Bus / 47 Seater", "rate": 700, "currency": "SAR"},
    ]
}

def load_rates():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return DEFAULT_RATES.copy()

def save_rates(rates):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(rates, f, ensure_ascii=False, indent=2)

if "rates" not in st.session_state:
    st.session_state.rates = load_rates()

rates = st.session_state.rates

st.title("🕋 Umrah Business Manager")
st.caption("Image rate lists • Package costing • PKR quotations")

tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Calculator",
    "🖼️ Rate Image Upload",
    "🏨 Manage Rates",
    "⚙️ Settings"
])

# ---------------- SETTINGS ----------------
if "settings" not in st.session_state:
    st.session_state.settings = {
        "SAR": 75.0,
        "USD": 280.0,
        "PKR": 1.0,
        "markup": 20.0
    }

settings = st.session_state.settings

def to_pkr(amount, currency):
    return float(amount) * float(settings.get(currency, 1))

with tab4:
    st.subheader("Currency aur profit settings")
    st.info("Exchange rates neeche sample values hain. Apne current rates enter karein.")

    settings["SAR"] = st.number_input(
        "1 SAR = kitne PKR?",
        min_value=0.01, value=float(settings["SAR"]), step=0.5
    )
    settings["USD"] = st.number_input(
        "1 USD = kitne PKR?",
        min_value=0.01, value=float(settings["USD"]), step=1.0
    )
    settings["PKR"] = 1.0

    settings["markup"] = st.number_input(
        "Cost par minimum markup (%)",
        min_value=20.0, max_value=500.0,
        value=max(20.0, float(settings["markup"])), step=1.0
    )

    if st.button("Save settings"):
        st.success("Settings current session ke liye save ho gayi hain.")

# ---------------- IMAGE OCR ----------------
with tab2:
    st.subheader("Monthly rate-list pictures upload karein")
    uploaded = st.file_uploader(
        "Hotel, transport, visa ya flight ki image",
        type=["png", "jpg", "jpeg"],
        accept_multiple_files=True
    )

    if uploaded:
        for file in uploaded:
            st.markdown(f"**File:** {file.name}")
            img = Image.open(file).convert("RGB")
            st.image(img, width=420)

            try:
                extracted = pytesseract.image_to_string(img)
                st.text_area(
                    "OCR se read hua text — verify karein",
                    extracted,
                    height=220,
                    key=f"ocr_{file.name}"
                )
                st.caption(
                    "OCR text ko check karke Manage Rates mein "
                    "correct values enter karein."
                )
            except Exception:
                st.warning(
                    "OCR available nahi hai. Tesseract install karein. "
                    "Aap image dekh kar rates manually bhi enter kar sakte hain."
                )

# ---------------- RATE MANAGEMENT ----------------
with tab3:
    st.subheader("Hotel rate list")
    hotel_df = pd.DataFrame(rates["hotels"])
    edited_hotels = st.data_editor(
        hotel_df,
        num_rows="dynamic",
        use_container_width=True,
        key="hotel_editor"
    )

    st.subheader("Transport rate list")
    transport_df = pd.DataFrame(rates["transport"])
    edited_transport = st.data_editor(
        transport_df,
        num_rows="dynamic",
        use_container_width=True,
        key="transport_editor"
    )

    st.subheader("Other service costs")
    visa_rate = st.number_input("Visa cost per person", min_value=0.0, value=0.0)
    flight_rate = st.number_input("Return flight per person", min_value=0.0, value=0.0)
    other_rate = st.number_input("Other expenses per person", min_value=0.0, value=0.0)
    service_currency = st.selectbox(
        "Visa, flight aur other costs ki currency",
        ["PKR", "SAR", "USD"]
    )

    if st.button("Save all rates", type="primary"):
        rates["hotels"] = edited_hotels.fillna("").to_dict("records")
        rates["transport"] = edited_transport.fillna("").to_dict("records")
        rates["services"] = {
            "visa": visa_rate,
            "flight": flight_rate,
            "other": other_rate,
            "currency": service_currency
        }
        save_rates(rates)
        st.success("Rates save ho gaye hain.")

# ---------------- PACKAGE CALCULATOR ----------------
with tab1:
    st.subheader("New Umrah package")

    hotels = rates.get("hotels", [])
    transport_options = rates.get("transport", [])

    if not hotels:
        st.warning("Pehle Manage Rates mein hotel rates add karein.")
    else:
        left, right = st.columns(2)

        with left:
            customer = st.text_input("Customer name", "Customer")
            travel_date = st.date_input("Travel date", value=date.today())
            adults = st.number_input(
                "Adults / paying passengers",
                min_value=1, max_value=500, value=4
            )
            children = st.number_input(
                "Children (separate pricing manually adjust karein)",
                min_value=0, max_value=200, value=0
            )
            nights_makkah = st.number_input(
                "Makkah nights", min_value=0, max_value=90, value=5
            )
            nights_madinah = st.number_input(
                "Madinah nights", min_value=0, max_value=90, value=5
            )

        with right:
            room_type = st.selectbox(
                "Room sharing",
                ["quad", "triple", "double"],
                format_func=lambda x: {
                    "quad": "Quad (4 sharing)",
                    "triple": "Triple (3 sharing)",
                    "double": "Double (2 sharing)"
                }[x]
            )

            makkah_hotels = [
                h for h in hotels if h.get("city") == "Makkah"
            ]
            madinah_hotels = [
                h for h in hotels if h.get("city") == "Madinah"
            ]

            makkah_names = [h["hotel"] for h in makkah_hotels]
            madinah_names = [h["hotel"] for h in madinah_hotels]

            mh = st.selectbox(
                "Makkah hotel",
                makkah_names if makkah_names else ["No hotel added"]
            )
            dh = st.selectbox(
                "Madinah hotel",
                madinah_names if madinah_names else ["No hotel added"]
            )

            transport_names = [
                t["name"] for t in transport_options
            ]
            chosen_transport = st.selectbox(
                "Transport vehicle",
                transport_names if transport_names else ["No vehicle added"]
            )
            transport_trips = st.number_input(
                "Total vehicle trips",
                min_value=0, max_value=100, value=2
            )

        st.markdown("### Additional costs")
        c1, c2, c3 = st.columns(3)
        with c1:
            visa = st.number_input("Visa per person (PKR)", min_value=0.0, value=0.0)
        with c2:
            flight = st.number_input("Return flight per person (PKR)", min_value=0.0, value=0.0)
        with c3:
            extras = st.number_input("Other cost per person (PKR)", min_value=0.0, value=0.0)

        if st.button("Calculate package", type="primary"):
            def find_hotel(city, name):
                return next(
                    (h for h in hotels
                     if h.get("city") == city and h.get("hotel") == name),
                    None
                )

            hotel_m = find_hotel("Makkah", mh)
            hotel_d = find_hotel("Madinah", dh)

            if (nights_makkah > 0 and hotel_m is None) or (
                nights_madinah > 0 and hotel_d is None
            ):
                st.error("Selected hotel ka rate available nahi hai.")
            else:
                rate_m = float(hotel_m.get(room_type, 0) or 0) if hotel_m else 0
                rate_d = float(hotel_d.get(room_type, 0) or 0) if hotel_d else 0

                curr_m = hotel_m.get("currency", "SAR") if hotel_m else "SAR"
                curr_d = hotel_d.get("currency", "SAR") if hotel_d else "SAR"

                makkah_pp = to_pkr(rate_m, curr_m) * nights_makkah
                madinah_pp = to_pkr(rate_d, curr_d) * nights_madinah

                vehicle = next(
                    (t for t in transport_options
                     if t["name"] == chosen_transport), None
                )
                transport_cost = 0
                if vehicle:
                    transport_cost = (
                        to_pkr(vehicle["rate"], vehicle.get("currency", "SAR"))
                        * transport_trips
                    )

                # Vehicle is charged once per trip, then allocated across adults.
                transport_pp = transport_cost / adults

                hotel_total_pp = makkah_pp + madinah_pp
                service_pp = visa + flight + extras
                cost_pp = hotel_total_pp + service_pp + transport_pp
                total_cost = cost_pp * adults
                profit_pp = cost_pp * settings["markup"] / 100
                selling_pp = cost_pp + profit_pp
                selling_total = selling_pp * adults

                st.session_state["last_quote"] = {
                    "customer": customer,
                    "date": str(travel_date),
                    "adults": adults,
                    "children": children,
                    "makkah_hotel": mh,
                    "madinah_hotel": dh,
                    "room": room_type.title(),
                    "makkah_nights": nights_makkah,
                    "madinah_nights": nights_madinah,
                    "transport": chosen_transport,
                    "cost_pp": cost_pp,
                    "total_cost": total_cost,
                    "profit_pp": profit_pp,
                    "selling_pp": selling_pp,
                    "selling_total": selling_total,
                    "markup": settings["markup"]
                }

                st.success("Package calculation complete")
                a, b, c = st.columns(3)
                a.metric("Cost per person", f"PKR {cost_pp:,.0f}")
                b.metric("Selling per person", f"PKR {selling_pp:,.0f}")
                c.metric("Total selling price", f"PKR {selling_total:,.0f}")

                st.write(f"**Total cost:** PKR {total_cost:,.0f}")
                st.write(f"**Estimated profit:** PKR {selling_total-total_cost:,.0f}")
                st.caption(
                    "Vehicle cost adults mein divide ki gayi hai. "
                    "Child fares, room occupancy aur flight rules verify karein."
                )

# ---------------- PDF QUOTATION ----------------
st.divider()
st.subheader("Customer quotation PDF")

quote = st.session_state.get("last_quote")

if quote:
    if st.button("Generate PDF quotation"):
        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        y = height - 55

        pdf.setFont("Helvetica-Bold", 20)
        pdf.drawString(45, y, "UMRAH PACKAGE QUOTATION")
        y -= 35

        pdf.setFont("Helvetica", 11)
        lines = [
            f"Customer: {quote['customer']}",
            f"Travel date: {quote['date']}",
            f"Passengers: {quote['adults']}",
            f"Makkah hotel: {quote['makkah_hotel']} ({quote['makkah_nights']} nights)",
            f"Madinah hotel: {quote['madinah_hotel']} ({quote['madinah_nights']} nights)",
            f"Room type: {quote['room']}",
            f"Transport: {quote['transport']}",
            "",
            f"Cost per person: PKR {quote['cost_pp']:,.0f}",
            f"Markup: {quote['markup']:.0f}%",
            f"Selling price per person: PKR {quote['selling_pp']:,.0f}",
            f"Total package price: PKR {quote['selling_total']:,.0f}",
            "",
            "Rates subject to availability and final confirmation.",
            "Flight, visa and hotel details should be reconfirmed before booking."
        ]

        for line in lines:
            pdf.drawString(45, y, line)
            y -= 23

        pdf.save()
        st.download_button(
            "Download quotation PDF",
            data=buffer.getvalue(),
            file_name="umrah_quotation.pdf",
            mime="application/pdf"
        )
else:
    st.info("Pehle Calculator tab mein package calculate karein.")