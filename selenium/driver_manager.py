"""Creación de un navegador visible con espera explícita de Selenium."""

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait

from config import WAIT_SECONDS


def iniciar_driver(browser="edge", timeout=WAIT_SECONDS):
    """Inicia Edge o Chrome visible y devuelve el navegador y WebDriverWait."""
    browser = browser.casefold()
    if browser == "edge":
        options = webdriver.EdgeOptions()
        options.add_argument("--start-maximized")
        driver = webdriver.Edge(options=options)
    else:
        options = webdriver.ChromeOptions()
        options.add_argument("--start-maximized")
        options.add_experimental_option("excludeSwitches", ["enable-logging"])
        driver = webdriver.Chrome(options=options)

    driver.set_page_load_timeout(30)
    return driver, WebDriverWait(driver, timeout)


def cerrar_driver(driver):
    """Cierra el navegador si se llegó a iniciar."""
    if driver is not None:
        try:
            driver.quit()
        except Exception:
            pass
