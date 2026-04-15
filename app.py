import streamlit as st
import time
import json
import re
from datetime import datetime
from difflib import SequenceMatcher
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
import warnings
import traceback

warnings.filterwarnings("ignore")

# Page config
st.set_page_config(
    page_title="Maldives Business Registry",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Header
st.markdown("# 🏢 Maldives Business Registry")
st.markdown("### Search and Extract Business Information")
st.markdown("---")

# Sidebar info
with st.sidebar:
    st.header("📋 About")
    st.info("""
    **Maldives Business Registry Scraper**
    
    Extract business information including:
    - Registration Number
    - Business Type
    - Owner/Managing Director
    - Board of Directors
    - Shareholders
    - Business Names
    - Business Activities
    
    Data Source: https://business.egov.mv
    """)

# Helper functions
def _similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, str(a).lower().strip(), str(b).lower().strip()).ratio()

def find_best_match(search_term: str, candidates: list) -> tuple:
    if not candidates:
        return None, 0.0
    try:
        ranked = sorted(candidates, key=lambda c: _similarity(search_term, c), reverse=True)
        best = ranked[0]
        return best, _similarity(search_term, best)
    except:
        return candidates[0] if candidates else None, 0.5

# Initialize Chrome driver
@st.cache_resource
def setup_driver():
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        import shutil
        
        driver_path = ChromeDriverManager().install()
        chrome_path = shutil.which("google-chrome") or shutil.which("google-chrome-stable")

        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-blink-features=AutomationControlled")
        if chrome_path:
            options.binary_location = chrome_path
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        driver = webdriver.Chrome(service=Service(driver_path), options=options)
        return driver
    except Exception as e:
        st.error(f"Driver setup error: {str(e)}")
        return None

# Search functions
def search_business(driver, business_name: str) -> bool:
    try:
        if driver is None:
            st.error("Driver not initialized")
            return False
            
        driver.get("https://business.egov.mv/BusinessRegistry")
        time.sleep(5)
        
        search_box = driver.find_element(By.ID, "twotabsearchtextbox")
        if search_box is None:
            st.error("Search box not found")
            return False
            
        search_box.clear()
        search_box.send_keys(business_name)
        time.sleep(2)
        search_box.send_keys(Keys.RETURN)
        
        max_wait = 15
        for i in range(max_wait):
            try:
                page_source = driver.page_source
                if page_source and len(page_source) > 0:
                    time.sleep(2)
                    return True
            except:
                pass
            
            if i < max_wait - 1:
                time.sleep(1)
        
        return True
    except Exception as e:
        st.error(f"Search error: {str(e)}")
        return False

def extract_search_results(driver) -> list:
    try:
        if driver is None:
            return []
            
        page_source = driver.page_source
        if not page_source:
            return []
            
        soup = BeautifulSoup(page_source, "html.parser")
        results = []
        
        cards = soup.find_all("div", {"class": "feature_home"})
        
        for idx, card in enumerate(cards):
            try:
                h3 = card.find("h3")
                name = h3.get_text(strip=True) if h3 else "N/A"
                
                p_tags = card.find_all("p")
                business_type = p_tags[0].get_text(strip=True) if len(p_tags) > 0 else "N/A"
                status = p_tags[1].get_text(strip=True) if len(p_tags) > 1 else "N/A"
                
                link = card.find("a")
                link_href = link.get("href", "") if link else ""
                
                reg_match = re.search(r"/ViewDetails/(\d+)", link_href)
                reg_number = reg_match.group(1) if reg_match else "N/A"
                
                if business_type.lower() not in ["business name", "logo", "permit", "license"]:
                    result = {
                        "name": name,
                        "reg_number": reg_number,
                        "type": business_type,
                        "status": status,
                        "link_href": link_href,
                        "row_index": idx,
                    }
                    results.append(result)
            except Exception as e:
                pass
        
        return results
    except Exception as e:
        st.error(f"Extract results error: {str(e)}")
        return []

def select_and_navigate(driver, search_term: str, results: list) -> tuple:
    try:
        if not results or driver is None:
            return False, None

        names = [r["name"] for r in results]
        best_name, score = find_best_match(search_term, names)
        best_result = next((r for r in results if r["name"] == best_name), None)

        if score < 0.5:
            return False, None

        if best_result and best_result.get("link_href"):
            link_href = best_result["link_href"]
            if not link_href.startswith("http"):
                link_href = "https://business.egov.mv" + link_href
            
            driver.get(link_href)
            time.sleep(5)
            return True, best_result
            
        return False, best_result
    except Exception as e:
        st.error(f"Navigation error: {str(e)}")
        return False, None

def extract_business_overview(driver) -> dict:
    try:
        if driver is None:
            return {"type": "N/A", "registration_number": "N/A", "managing_director": "N/A", "owner": "N/A", "board_of_directors": [], "shareholders": [], "business_names": [], "business_activities": []}
        
        page_source = driver.page_source
        if not page_source:
            return {"type": "N/A", "registration_number": "N/A", "managing_director": "N/A", "owner": "N/A", "board_of_directors": [], "shareholders": [], "business_names": [], "business_activities": []}
        
        soup = BeautifulSoup(page_source, "html.parser")
        overview = {
            "type": "N/A",
            "registration_number": "N/A",
            "managing_director": "N/A",
            "owner": "N/A",
            "board_of_directors": [],
            "shareholders": [],
            "business_names": [],
            "business_activities": [],
        }

        all_text = soup.get_text()
        
        # Extract registration number
        reg_match = re.search(r'(SP|PVT|PART|COOP|LLC|BN)-[\d\w]+/\d{4}', all_text)
        if reg_match:
            overview["registration_number"] = reg_match.group(0).strip()
        
        # Extract type
        type_match = re.search(r"\[\s*([^\]]+?Proprietorship|Company|Partnership|Cooperative[^\]]*)\s*\]", all_text)
        if type_match:
            overview["type"] = type_match.group(1).strip()
        
        # Extract owner/MD
        for heading in soup.find_all(["h3", "h4", "h5", "strong"]):
            try:
                heading_lower = heading.get_text().lower()
                
                if "owner" in heading_lower and "managing director" not in heading_lower:
                    next_elem = heading.find_next(["p", "div", "span", "td"])
                    if next_elem:
                        owner_text = next_elem.get_text(strip=True)
                        if owner_text and owner_text not in ["N/A", "-", ""]:
                            overview["owner"] = owner_text
                            overview["managing_director"] = owner_text
                            break
            except:
                pass
        
        if overview["managing_director"] == "N/A":
            for heading in soup.find_all(["h3", "h4", "h5", "strong"]):
                try:
                    if "managing director" in heading.get_text().lower():
                        next_elem = heading.find_next(["p", "div", "span", "td"])
                        if next_elem:
                            md_text = next_elem.get_text(strip=True)
                            if md_text and md_text not in ["N/A", "-", ""]:
                                overview["managing_director"] = md_text
                                break
                except:
                    pass
        
        # Extract board of directors
        for heading in soup.find_all(["h3", "h4", "h5"]):
            try:
                if "board of director" in heading.get_text().lower() or ("director" in heading.get_text().lower() and "business" not in heading.get_text().lower()):
                    table = heading.find_next("table")
                    if table:
                        rows = table.find_all("tr")
                        for row in rows[1:]:
                            cells = row.find_all("td")
                            if len(cells) >= 1:
                                name = cells[0].get_text(strip=True)
                                appointed_date = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                                
                                if name and len(name) > 2 and name not in ["Name", "N/A", "-"]:
                                    director_info = f"{name}"
                                    if appointed_date and appointed_date != "Appointed Date":
                                        director_info += f" (Appointed: {appointed_date})"
                                    
                                    if director_info not in overview["board_of_directors"]:
                                        overview["board_of_directors"].append(director_info)
                    break
            except:
                pass
        
        # Extract shareholders
        for heading in soup.find_all(["h3", "h4", "h5"]):
            try:
                if "shareholder" in heading.get_text().lower():
                    table = heading.find_next("table")
                    if table:
                        rows = table.find_all("tr")
                        for row in rows[1:]:
                            cells = row.find_all("td")
                            if len(cells) >= 1:
                                name = cells[0].get_text(strip=True)
                                join_date = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                                
                                if name and len(name) > 2 and name not in ["Name", "N/A", "-"]:
                                    shareholder_info = f"{name}"
                                    if join_date and join_date != "Join Date":
                                        shareholder_info += f" (Join: {join_date})"
                                    
                                    if shareholder_info not in overview["shareholders"]:
                                        overview["shareholders"].append(shareholder_info)
                    break
            except:
                pass
        
        # Extract business names
        for heading in soup.find_all("h3"):
            try:
                if "business name" in heading.get_text().lower():
                    table = heading.find_next("table")
                    if table:
                        rows = table.find_all("tr")
                        for row in rows[1:]:
                            cells = row.find_all("td")
                            if len(cells) >= 1:
                                name = cells[0].get_text(strip=True)
                                if name and len(name) > 2 and name not in ["Name", "N/A", "-"]:
                                    if name not in overview["business_names"]:
                                        overview["business_names"].append(name)
                    break
            except:
                pass
        
        # Extract business activities
        try:
            activities_dict = {}
            all_headings = soup.find_all("h3")
            
            for heading in all_headings:
                heading_text = heading.get_text().lower()
                if "business activit" in heading_text and "license" not in heading_text and "permit" not in heading_text:
                    current = heading
                    section_html = ""
                    
                    while current:
                        current = current.find_next()
                        if current is None:
                            break
                        if current.name == "h3":
                            break
                        section_html += current.get_text()
                    
                    if "does not have" in section_html.lower():
                        overview["business_activities"] = ["No registered business activity"]
                        break
                    
                    table = heading.find_next("table")
                    if table:
                        rows = table.find_all("tr")
                        for row in rows[1:]:
                            cells = row.find_all("td")
                            if len(cells) >= 2:
                                activity = cells[1].get_text(strip=True)
                                if activity and len(activity) > 5 and activity not in ["Business Activity", "N/A", "-", "License Type"]:
                                    if not any(skip in activity.lower() for skip in ["license", "permit", "upn", "number", "issued", "expiry", "status"]):
                                        activity = re.sub(r'\s*x\s*\(\d+\)\s*$', '', activity).strip()
                                        if activity in activities_dict:
                                            activities_dict[activity] += 1
                                        else:
                                            activities_dict[activity] = 1
                    break
            
            if not overview["business_activities"]:
                if activities_dict:
                    for activity, count in sorted(activities_dict.items()):
                        if count > 1:
                            formatted = f"{activity} x ({count})"
                        else:
                            formatted = activity
                        overview["business_activities"].append(formatted)
                else:
                    overview["business_activities"] = ["No registered business activity"]
        except:
            overview["business_activities"] = ["No registered business activity"]
        
        return overview
    except Exception as e:
        st.error(f"Extract overview error: {str(e)}")
        return {"type": "N/A", "registration_number": "N/A", "managing_director": "N/A", "owner": "N/A", "board_of_directors": [], "shareholders": [], "business_names": [], "business_activities": []}

# Main UI
col1, col2 = st.columns([3, 1])

with col1:
    search_term = st.text_input(
        "🔎 Search Business",
        placeholder="e.g., ELITE PLAZA, Magnolia, Mild Steel",
        help="Enter business name (minimum 3 characters)"
    )

with col2:
    search_button = st.button("🔍 Search", use_container_width=True, key="search_btn")

st.markdown("---")

# Search logic
if search_button:
    if not search_term or len(search_term) < 3:
        st.warning("⚠️ Please enter at least 3 characters")
    else:
        with st.spinner("🔄 Searching registry... This may take 30-60 seconds"):
            driver = None
            try:
                driver = setup_driver()
                
                if driver is None:
                    st.error("❌ Could not initialize driver")
                elif not search_business(driver, search_term):
                    st.error("❌ Search failed")
                else:
                    results = extract_search_results(driver)
                    
                    if not results:
                        st.error("❌ No results found")
                    else:
                        clicked, best = select_and_navigate(driver, search_term, results)
                        
                        if not clicked or best is None:
                            st.error("❌ Could not navigate to details page")
                        else:
                            overview = extract_business_overview(driver)
                            
                            final_reg_number = overview["registration_number"]
                            if final_reg_number == "N/A":
                                final_reg_number = best.get("reg_number", "N/A")
                            
                            st.success("✅ Data extracted successfully!")
                            
                            st.markdown("### 📊 Business Overview")
                            
                            col1, col2, col3, col4 = st.columns(4)
                            
                            with col1:
                                st.metric("📋 Registration #", final_reg_number)
                            with col2:
                                st.metric("🏢 Type", overview["type"])
                            with col3:
                                st.metric("📦 Business Names", len(overview["business_names"]))
                            with col4:
                                st.metric("📈 Activities", len(overview["business_activities"]))
                            
                            st.markdown("---")
                            
                            st.subheader("👤 Owner/Managing Director")
                            st.write(f"**{overview['managing_director']}**")
                            
                            if overview["board_of_directors"]:
                                st.subheader("🏛️ Board of Directors")
                                for director in overview["board_of_directors"]:
                                    st.write(f"• {director}")
                            
                            if overview["shareholders"]:
                                st.subheader("👥 Shareholders")
                                for shareholder in overview["shareholders"]:
                                    st.write(f"• {shareholder}")
                            
                            st.subheader("🏪 Business Names")
                            if overview['business_names']:
                                for name in overview['business_names']:
                                    st.write(f"• {name}")
                            else:
                                st.info("No business names registered")
                            
                            st.subheader("📋 Business Activities")
                            if overview['business_activities']:
                                for activity in overview['business_activities']:
                                    st.write(f"• {activity}")
                            else:
                                st.info("No business activities registered")
                            
                            st.markdown("---")
                            
                            st.subheader("📥 Download Results")
                            
                            result_json = {
                                "search_term": search_term,
                                "business_name": best["name"],
                                "registration_number": final_reg_number,
                                "type": overview["type"],
                                "managing_director": overview["managing_director"],
                                "board_of_directors": overview["board_of_directors"],
                                "shareholders": overview["shareholders"],
                                "business_names": overview["business_names"],
                                "business_activities": overview["business_activities"],
                                "timestamp": datetime.now().isoformat(),
                            }
                            
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.download_button(
                                    label="📄 Download JSON",
                                    data=json.dumps(result_json, indent=2),
                                    file_name=f"{best['name']}_registry.json",
                                    mime="application/json"
                                )
                            
                            with col2:
                                csv_data = "Business Name,Registration #,Type,Owner/MD,Board Count,Shareholders Count,Business Names,Activities\n"
                                csv_data += f'"{best["name"]}","{final_reg_number}","{overview["type"]}","{overview["managing_director"]}",{len(overview["board_of_directors"])},{len(overview["shareholders"])},{len(overview["business_names"])},{len(overview["business_activities"])}\n'
                                
                                st.download_button(
                                    label="📊 Download CSV",
                                    data=csv_data,
                                    file_name=f"{best['name']}_registry.csv",
                                    mime="text/csv"
                                )
                            
            except Exception as e:
                st.error(f"❌ Unexpected error: {str(e)}")
                st.write(traceback.format_exc())
            finally:
                if driver:
                    try:
                        driver.quit()
                    except:
                        pass

st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; margin-top: 50px;'>
    <p>Made with ❤️ for Maldives Business Intelligence</p>
    <p><small>Data Source: <a href='https://business.egov.mv' target='_blank'>Maldives Business Registry</a></small></p>
</div>
""", unsafe_allow_html=True)
