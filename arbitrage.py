#!/usr/bin/python

import sys

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import StaleElementReferenceException

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def arbitrage(factors):
    result = []
    for i in range(len(factors)):
        result.append(1 / factors[i])
    total = sum(result)
    for i in range(len(result)):
        result[i] /= total
    return result, result[0] * factors[0]

def show_result(factors, result, value = 1):
    valued = result.copy()
    for i in range(len(valued)):
        valued[i] *= value
    print(factors)
    print(valued)
    print(str((result[0] * factors[0] - 1) * 100) + "%")

class Combiner:
    def __init__(self):
        self.best_index = []
        self.best = []
        self.factors = {}

    def update_best(self):
        self.best = []
        self.best_index = []
        for identifier, factors in self.factors.items():
            if self.best:
                for i in range(len(self.best)):
                    if factors[i] > self.best[i]:
                        self.best[i] = factors[i]
                        self.best_index[i] = identifier
            else:
                self.best = factors.copy()
                self.best_index = [identifier] * len(factors)

    def add(self, identifier, factors, show = False):
        self.factors[identifier] = factors
        if show:
            show_result(factors, arbitrage(factors)[0])
        self.update_best()

    def gain(self):
        if self.best:
            _, gain = arbitrage(self.best)
            return gain
        return None

    def show(self, value = 1):
        if self.best:
            print(self.best_index)
            result, gain = arbitrage(self.best)
            show_result(self.best, result, value)

def add_analyser(analyser, url):
    options = Options()
    #options.headless = True
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    driver = webdriver.Chrome(options=options)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": "Object.defineProperty(navigator, 'webdriver', { get: () => undefined })"})
    driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.53 Safari/537.36'})
    driver.get(url)
    analysers.append((analyser, driver))

def run_analysers():
    global analysers
    for analyser, driver in analysers:
        analyser(driver)

def close_drivers():
    global analysers
    for _, driver in analysers:
        driver.close()

def unify(a, b):
    if a in b:
        return b
    if b in a:
        return a
    return None

def adapt_key(key):
    global combiners
    left, right = key
    for left_other, right_other in combiners:
        unified_left = unify(left, left_other)
        unified_right = unify(right, right_other)
        if unified_left is not None and unified_right is not None:
            unified = (unified_left, unified_right)
            old = (left_other, right_other)
            if old != unified:
                combiners[unified] = combiners[old]
                del combiners[old]
            return unified
    return key

def betfair(driver):
    global combiners
    items = driver.find_elements_by_class_name("event-information")
    for item in items:
        try:
            names = item.find_elements_by_class_name("team-name")
        except StaleElementReferenceException:
            continue
        for i in range(len(names)):
            names[i] = names[i].text
            split = names[i].split(" ")
            if len(split) > 1 and split[0]:
                split[0] = split[0][0]
            names[i] = " ".join(split)
        key = adapt_key(tuple(names))
        if key in combiners:
            combiner = combiners[key]
        else:
            combiner = Combiner()
            combiners[key] = combiner
        fields = item.find_elements_by_class_name("ui-runner-price")
        skip = False
        prices = []
        factors = []
        for field in fields:
            price = field.text.strip()
            prices.append(price)
            if price == "":
                skip = True
            else:
                if price == "EVS":
                    factor = 2
                else:
                    components = price.split("/")
                    factor = 1 + float(components[0]) / float(components[1])
                factors.append(factor)
        if not skip:
            combiner.add("betfair", factors)

def _888sport(driver):
    global combiners
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "bet-card"))
    )
    items = driver.find_elements_by_class_name("bet-card")
    for item in items:
        try:
            names = item.find_elements_by_class_name("featured-matches-widget__event-competitor")
        except StaleElementReferenceException:
            continue
        if names:
            for i in range(len(names)):
                names[i] = names[i].text
                if ',' in names[i]:
                    index = names[i].index(',')
                    names[i] = names[i][index + 2:index + 3] + " " + names[i][:index]
            key = adapt_key(tuple(names))
            if key in combiners:
                combiner = combiners[key]
            else:
                combiner = Combiner()
                combiners[key] = combiner
            fields = item.find_elements_by_class_name("bb-sport-event__selection")
            prices = []
            factors = []
            for field in fields:
                price = field.text.strip()
                prices.append(price)
                if price != "":
                    components = price.split("/")
                    factor = 1 + float(components[0]) / float(components[1])
                    factors.append(factor)
            combiner.add("888sport", factors)

def bet365(driver):
    global combiners

combiners = {}
analysers = []

if len(sys.argv) > 1:
    value = float(sys.argv[1])
else:
    value = 1
combiner = Combiner()
while True:
    try:
        line = input()
    except EOFError:
        combiner.show(value)
        quit()
    items = line.split(" ")
    identifier = items[0]
    odds = items[1:]
    factors = []
    for odd in odds:
        components = odd.split("/")
        if len(components) == 1:
            factor = float(components[0])
        else:
            factor = 1 + float(components[0]) / float(components[1])
        factors.append(factor)
    combiner.add(identifier, factors, True)
quit()

add_analyser(betfair, "https://www.betfair.com/sport/tennis")
add_analyser(_888sport, "https://www.888sport.com/tennis")
#add_analyser(bet365, "https://www.bet365.com/#/AC/B13/C1/D50/E2/F163/")
run_analysers()
for key in combiners:
    gain = combiners[key].gain()
    if gain is not None:
        print(key)
        combiners[key].show()
for key in combiners:
    gain = combiners[key].gain()
    if gain is not None and gain > 1:
        print(key)
        combiners[key].show()
close_drivers()
