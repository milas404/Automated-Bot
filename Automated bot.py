import time, os, random,sys, requests
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait ,Select
from selenium.webdriver.support import expected_conditions as EC
from twocaptcha import TwoCaptcha
from dotenv import load_dotenv
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import logging
from selenium.common.exceptions import StaleElementReferenceException
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

class SuppressUCError:
    def write(self, msg):
        if "Chrome.__del__" in msg or "WinError 6" in msg:
            return
        sys.__stderr__.write(msg)

    def flush(self):
        sys.__stderr__.flush()

sys.stderr = SuppressUCError()


# Load Environment Variables
load_dotenv()
API_KEY = os.getenv("API_KEY")
results = {
     "Login Success": False,
     "Login Time (s)": None,
     "Add-to-Cart Success": False,
     "Add-to-Cart Time (s)": None,
     "Checkout Click Success": False,
     "Checkout Click Time (s)": None,
     "Total Script Time (s)": None,
     "Errors": []
    }


# Human-like typing 
def human_type(element, text):
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.05, 0.2))

# Human-like delay 
def human_like_delay(min_sec=1.0, max_sec=3.0):
    delay = random.uniform(min_sec, max_sec)
    logging.info(f"Sleeping {delay:.2f} seconds to mimic human behavior")
    time.sleep(delay)


# Solve hCaptcha with 2Captcha
def solve_hcaptcha(site_key, url):
     print("[+] Sending hCaptcha to 2Captcha...")
     solver = TwoCaptcha(API_KEY)
     result = solver.hcaptcha(sitekey=site_key, url=url)
     print("[+] hCaptcha solved!")
     return result["code"]

def find_in_shadow(driver, selectors, timeout=12):
    """
    Iteratively traverse shadow roots given a list of selectors.
    selectors = ["se-account-app", "se-login", "input#email"]
    Returns a WebElement or raises TimeoutException.
    """
    def _script(selectors):
        return """
        const sels = arguments[0];
        // We will walk up to the penultimate selector, obtaining the shadowRoot each time.
        let node = document;
        for (let i = 0; i < sels.length - 1; ++i) {
            const sel = sels[i];
            const el = node.querySelector(sel);
            if (!el) return null;
            if (!el.shadowRoot) return null;
            node = el.shadowRoot;
        }
        // final selector is queried inside the last shadowRoot (or document if only one selector)
        const lastSel = sels[sels.length - 1];
        return node.querySelector(lastSel);
        """
    wait = WebDriverWait(driver, timeout)
    # Wait until script returns element
    el = wait.until(lambda d: d.execute_script(_script(selectors), selectors))
    return el

def shadow_find(driver, selectors):
    script = """
    const root = document;
    const list = arguments[0];
    let node = root;
    for (let sel of list) {
        node = (node === document)
            ? node.querySelector(sel)
            : node.shadowRoot.querySelector(sel);
        if (!node) return null;
    }
    return node;
    """
    return driver.execute_script(script, selectors)


# Login Function
def login_pokemoncenter(email, password):
    t0 = time.time()
    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")
    driver = uc.Chrome(version_main =146,use_subprocess=True)
    wait = WebDriverWait(driver, 20)

    # Step 1: Open Login Page
    try:
        driver.get("https://www.pokemoncenter.com/account/login")
        time.sleep(5)

        # Fill email and password
        email_box = wait.until(EC.visibility_of_element_located((By.ID, "login-email")))
        password_box = wait.until(EC.visibility_of_element_located((By.ID, "login-password")))

        human_type(email_box, email)
        human_type(password_box, password)

        # Click Sign In
        sign_in_button = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "button[type='submit'][aria-label='Sign in to my account']")
        ))
        driver.execute_script("arguments[0].click();", sign_in_button)

        time.sleep(10)
        
        print("Login successfully")
        time.sleep(5)
        print("Home page viewed")

        #Search product through link
        try:
            # Open Product Page
            driver.get("https://www.pokemoncenter.com/product/699-16774/pokemon-tcg-sun-and-moon-elite-trainer-box-lunala")
            #driver.get("https://www.pokemoncenter.com/product/71-10335-101/pokemon-30th-celebration-stemless-glasses-2-pack")
            print("Product opened directly through link")

        except Exception as e:
            print("Direct link failed, switching to search")

            # OPTIONAL: click search icon first
            try:
                search_icon = wait.until(EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "button[aria-label='Search']")
                ))
                search_icon.click()
            except:
                pass  # if no search icon, continue

            # Wait for search input
            search_box = wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "input[type='search']")
            ))

            search_box.click()
            search_box.clear()

            keyword = "elite trainer"
            human_type(search_box, keyword)
            print("Keyword Typed")
            search_box.send_keys(Keys.ENTER)

            # Wait until URL changes to search page 
            wait.until(EC.url_contains("search"))

            # Wait longer for products
            products = wait.until(EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "a[href*='/product/']")
            ))
            print("Item searched")

            # Find the first visible product
            first_visible_product = None
            for product in products:
                if product.is_displayed():
                    first_visible_product = product
                    print("Product detected")
                    break

            if first_visible_product is None:
                raise Exception("No visible product found")

            # Scroll into view (prevents interception issues)
            driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});",
                first_visible_product
            )

            # Small pause helps React animation overlays
            time.sleep(1)

            # Click using JS 
            driver.execute_script("arguments[0].click();", first_visible_product)
            print("First product Clicked")

            # Wait for product page to load (URL changes to /product/)
            wait.until(EC.url_contains("/product/"))
            
            # Wait for button container to load
            wait.until(EC.presence_of_element_located(
                (By.TAG_NAME, "button")
            ))

        # Handle variant selection (if exists)
        try:
            variant_buttons = driver.find_elements(By.CSS_SELECTOR, "button[role='radio']")
            for btn in variant_buttons:
                if btn.is_enabled() and btn.is_displayed():
                    driver.execute_script("arguments[0].click();", btn)
                    break
        except:
            pass


        # Wait for Add to Cart button
        add_to_cart_btn = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, "//button[contains(., 'Add to Cart')]"))
        )

        # Check if button is clickable (important!)
        if add_to_cart_btn.is_enabled() and add_to_cart_btn.is_displayed():
            print("Product AVAILABLE! Adding to cart...")
            # Quantity Selected
            quantity = 1
            print("Add to cart page loaded")

            for i in range(quantity):
                try:
                    # Scroll into view
                    driver.execute_script(
                        "arguments[0].scrollIntoView({block: 'center'});",
                        add_to_cart_btn
                    )

                    time.sleep(1)

                    # Click using JavaScript
                    driver.execute_script("arguments[0].click();", add_to_cart_btn)
                    print(f"Added item to cart {i+1} times")

                    # Wait for cart confirmation
                    wait.until(EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "[data-testid='mini-cart'], a[href*='/cart']")
                    ))

                    time.sleep(2)  # allow UI to reset

                    # Close mini cart if blocking next click
                    try:
                        close_btn = driver.find_element(By.XPATH, "//button[contains(@class,'close')]")
                        driver.execute_script("arguments[0].click();", close_btn)
                    except:
                        pass

                except Exception as e:
                    print("Error adding item:", e)

        else:
            print("Not available yet... retrying")


        # Go to Cart
        driver.get("https://www.pokemoncenter.com/cart")
        print("Added to cart")

        # Click Checkout
        checkout_btn = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//button[.//text()[contains(., 'Checkout')]]")
        ))
        driver.execute_script("arguments[0].click();", checkout_btn)
        time.sleep(10)
        
        # CLICK CONTINUE BUTTON
        try:
            print("Clicking Continue...")

            continue_btn = wait.until(EC.element_to_be_clickable((
                By.XPATH, "//button[.//text()[contains(., 'CONTINUE')]]"
            )))

            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", continue_btn)
            time.sleep(1)
            driver.execute_script("arguments[0].click();", continue_btn)

            print("Continue clicked")

        except Exception as e:
            print("Continue button error:", e)
        time.sleep(6)

        # Select Credit Card
        dropdown = Select(wait.until(EC.element_to_be_clickable((By.ID, "billing-selector"))))
        dropdown.select_by_visible_text("Credit/Debit Card")
        print("Card Selected")

        time.sleep(3)


        def inspect_and_fill_iframes(driver):
            wait.until(EC.presence_of_all_elements_located((By.TAG_NAME, "iframe")))
            
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            print(f"Found {len(iframes)} iframes\n")

            card_done = False
            cvv_done = False

            for i in range(len(iframes)):
                try:
                    # Re-fetch iframe 
                    iframe = driver.find_elements(By.TAG_NAME, "iframe")[i]

                    # Print iframe info
                    print(f"\n--- IFRAME {i} ---")
                    print("ID:", iframe.get_attribute("id"))
                    print("NAME:", iframe.get_attribute("name"))
                    print("SRC:", iframe.get_attribute("src"))

                    # Switch to iframe
                    driver.switch_to.frame(iframe)
                    time.sleep(2)

                    # Wait for inputs inside iframe
                    inputs = driver.find_elements(By.TAG_NAME, "input")
                    print(f"Inputs found: {len(inputs)}")

                    for inp in inputs:
                        name = (inp.get_attribute("name") or "").lower()
                        placeholder = (inp.get_attribute("placeholder") or "").lower()

                        print("   → input:", name, "|", placeholder)

                        field = name + " " + placeholder

                        # CARD NUMBER
                        if not card_done and ("card" in field or "number" in field):
                            print("Typing CARD NUMBER")
                            inp.click()
                            inp.clear()
                            inp.send_keys("4242424242424242")
                            card_done = True
                            time.sleep(1)

                        # CVV
                        elif not cvv_done and ("securitycode" in field or "cvc" in field):
                            print("Typing CVV")
                            inp.click()
                            inp.clear()
                            inp.send_keys("123")
                            cvv_done = True
                            time.sleep(1)

                        if card_done and cvv_done:
                            break
                    # Go back to main page
                    driver.switch_to.default_content()

                except Exception as e:
                    print("Error in iframe:", e)
                    driver.switch_to.default_content()
                    continue

            return card_done, cvv_done


        # RUN
        card_done, cvv_done = inspect_and_fill_iframes(driver)

        print("\nRESULT:")
        print("Card filled:", card_done)
        print("CVV filled:", cvv_done)


        
        if not card_done or not cvv_done:
            print("Autofill failed (expected on protected checkout)")

            input("Enter card manually, then press ENTER...")

        #Select Month And Year
        dropdown = Select(wait.until(EC.element_to_be_clickable((By.ID, "expiryMonth"))))
        dropdown.select_by_visible_text("12")
        print("Month Selected")
        
        dropdown = Select(wait.until(EC.element_to_be_clickable((By.ID, "expiryYear"))))
        dropdown.select_by_visible_text("2030")
        print("Year Selected")

        print("Clicking Continue...")

        continue_btn = wait.until(EC.element_to_be_clickable((
                By.XPATH, "//button[.//text()[contains(., 'CONTINUE')]]"
            )))

        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", continue_btn)
        time.sleep(1)
        driver.execute_script("arguments[0].click();", continue_btn)

        print("Continue clicked")

        print("Clicking Place Order")

        placeOrder_btn = wait.until(EC.element_to_be_clickable((
                By.XPATH, "//button[.//text()[contains(., 'PLACE ORDER')]]"
            )))

        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", placeOrder_btn)
        time.sleep(1)
        driver.execute_script("arguments[0].click();", placeOrder_btn)

        print("Order Placed Clicked")
        print("Job Done Successfully")

    except Exception as e:
        print("ERROR OCCURRED:")

    finally:
        print("Error occured.Browser closed")
        try:
            driver.quit()
        except:
            pass
    

# Run
driver = login_pokemoncenter("abcd@gmail.com", "Pass@2025Pass")
