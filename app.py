import os
import random
import streamlit as st
from decimal import Decimal
from engine.calculator import ProrationCalculator

st.set_page_config(page_title="Operational Capability Audit", layout="centered")

st.title("Enterprise Billing Capability Audit")
st.caption("Operational Stress-Test: SaaS Proration & Clawback (3-Minute Simulation)")

if "scenario" not in st.session_state:
    acv = float(random.randint(25, 85) * 1000)
    days_elapsed = random.randint(45, 110)
    discount = float(random.randint(2, 6) * 1000)
    
    st.session_state.scenario = {
        "acv": acv,
        "days_elapsed": days_elapsed,
        "discount": discount,
        "company": random.choice(["Acme Cloud Corp", "Apex Logistics", "Vanguard Financial", "Starlight Media"])
    }
    st.session_state.audit_result = None

sc = st.session_state.scenario
calc = ProrationCalculator(acv=sc["acv"], days_elapsed=sc["days_elapsed"], discount=sc["discount"])

@st.cache_data(show_spinner="Formatting scenario ticket...")
def get_scenario_ticket(company, acv, days_elapsed, discount):
    # Standard clean enterprise fallback ticket
    fallback_ticket = f"""
**From:** Billing Escalations &lt;escalations@{company.lower().replace(' ', '')}.com&gt;  
**Subject:** Mid-Term Contract Cancellation & Settlement Request  

Hi Operations Team,  
**{company}** has requested immediate termination of contract **#CNT-88219** after **{days_elapsed} days** of service.  

* **Annual Contract Value (excl. VAT):** ${acv:,.2f}  
* **Contract Term:** 365 Days  
* **Signing Incentive:** ${discount:,.2f} onboarding credit (Subject to full 180-day retention clause)  
* **Early Termination Fee:** 20% on gross unearned balance  
* **Tax Jurisdiction:** 15% Standard VAT  

Please compute the exact final net payout due to the customer per standard operating procedures.
"""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return fallback_ticket

    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        prompt = f"""
Generate an internal corporate escalation ticket from a Customer Success Manager about a mid-term contract cancellation.
Use these EXACT values:
- Company Name: {company}
- Contract Length: 365 days
- Days Active: {days_elapsed} days
- Annual Contract Value: ${acv:,.2f}
- Early Termination Penalty: 20%
- Onboarding Credit: ${discount:,.2f} (clawed back in full if cancelled before 180 days)
- Tax: 15% VAT

Keep it professional, urgent, and concise. Do NOT do any math calculations. Format as markdown.
"""
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return response.text
    except Exception:
        # If Gemini's API gateway rejects the AQ key, cleanly return the standard scenario ticket
        return fallback_ticket

st.markdown("### Incoming Task Context")
ticket_text = get_scenario_ticket(sc["company"], sc["acv"], sc["days_elapsed"], sc["discount"])
st.info(ticket_text)

st.markdown("---")
st.subheader("Your Operational Output")
st.write("Calculate the final net payout (including VAT) due to the customer.")

user_payout = st.number_input(
    "Enter Net Settlement Amount ($):",
    min_value=0.0,
    max_value=200000.0,
    step=0.01,
    format="%.2f"
)

col1, col2 = st.columns([1, 2])

with col1:
    if st.button("Submit Audit Calculation", type="primary"):
        st.session_state.audit_result = calc.audit(user_payout)

with col2:
    if st.button("New Randomized Scenario"):
        st.session_state.clear()
        st.rerun()

if st.session_state.audit_result:
    res = st.session_state.audit_result
    st.markdown("---")
    st.subheader("Automated Competency Evaluation")

    if res["verdict"] == "PASS":
        st.success("VERDICT: PASS — Calculation exact to the cent.")
    else:
        st.error(f"VERDICT: FAIL — Operational Variance: ${res['variance']:+,.2f}")
        
        if res["error_code"] == "ERR_ML_01":
            st.warning("**Diagnostic Failure: DISCOUNT_CLAWBACK_OMITTED**  \nThe candidate omitted the 180-day conditional clawback clause, over-refunding the client.")
        elif res["error_code"] == "ERR_ML_02":
            st.warning("**Diagnostic Failure: INVERTED_ORDER_OF_OPERATIONS**  \nThe candidate deducted the discount prior to computing the 20% penalty.")
        elif res["error_code"] == "ERR_ML_03":
            st.warning("**Diagnostic Failure: GROSS_TAX_APPLICATION**  \nThe candidate applied the 15% VAT to the gross balance instead of the net settlement base.")
        else:
            st.warning("**Diagnostic Failure: UNCLASSIFIED_CALCULATION_ERROR**  \nGeneral arithmetic failure.")
