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
            if self.best_index[0] != "*":
                print(self.best_index)
            result, gain = arbitrage(self.best)
            show_result(self.best, result, value)

combiners = {}
analysers = []

options = Options()
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option('useAutomationExtension', False)
driver = webdriver.Chrome(options=options)
driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": "Object.defineProperty(navigator, 'webdriver', { get: () => undefined })"})
driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.53 Safari/537.36'})
last_overview = "https://www.oddschecker.com/tennis"
driver.get(last_overview)

if len(sys.argv) > 1:
    value = float(sys.argv[1])
else:
    value = 1
combiner = Combiner()
last_results = []
last_distribution = []
last_bookies = []
while True:
    try:
        line = input("> ")
    except EOFError:
        combiner.show(value)
        driver.close()
        quit()
    arguments = line.split(" ")
    command = arguments[0]
    if command == "calc":
        odds = arguments[1:]
        factors = []
        for odd in odds:
            components = odd.split("/")
            if len(components) == 1:
                factor = float(components[0])
            else:
                factor = 1 + float(components[0]) / float(components[1])
            factors.append(factor)
        combiner.add("*", factors, True)
    elif command == "ov" or command == "overview":
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "match-on"))
        )
        items = driver.find_elements_by_class_name("match-on")
        results = []
        for item in items:
            try:
                fields = item.find_elements_by_tag_name("td")
            except StaleElementReferenceException:
                continue
            if fields:
                skip = False
                factors = []
                link = ""
                for field in fields:
                    c = field.get_attribute("class")
                    if "basket-add" in c:
                        components = field.text.split("/")
                        if len(components) == 2:
                            factor = 1 + float(components[0]) / float(components[1])
                            factors.append(factor)
                        else:
                            skip = True
                            break
                    elif "link-right" in c:
                        links = field.find_elements_by_tag_name("a")
                        if links:
                            link = links[0].get_attribute("href")
                if not skip:
                    result, gain = arbitrage(factors)
                    if gain > 1:
                        try:
                            in_play = len(item.find_elements_by_class_name("in-play")) > 0
                            names = item.find_elements_by_class_name("fixtures-bet-name")
                        except StaleElementReferenceException:
                            in_play = False
                            names = []
                        for i in range(len(names)):
                            names[i] = names[i].text
                        results.append((gain, in_play, names, factors, result, link))
        results.sort(key = lambda x: (0 if x[1] else 1, x[0]))
        first = True
        i = len(results)
        for gain, in_play, names, factors, result, _ in results:
            if first:
                first = False
            else:
                print()
            print("#" + str(i))
            if in_play:
                print("IN PLAY")
            print(names)
            show_result(factors, result, value)
            i -= 1
        last_results = results
        last_overview = driver.current_url
    elif command == "det" or command == "details":
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "diff-row"))
        )
        header = driver.find_elements_by_css_selector(".eventTableHeader td")
        items = driver.find_elements_by_class_name("diff-row")
        factors = []
        factor_bookies = []
        skip = False
        for item in items:
            try:
                fields = item.find_elements_by_tag_name("td")[1:]
            except:
                print("Failed to get row")
                skip = True
                break
            best = None
            best_bookie = None
            for field in fields:
                bookie = field.get_attribute("data-bk")
                if bookie is not None:
                    text = field.find_elements_by_tag_name("p")
                    if text:
                        text = text[0].text
                        if text != "SP":
                            components = text.split("/")
                            if len(components) == 1:
                                factor = 1 + float(components[0])
                            elif len(components) == 2:
                                factor = 1 + float(components[0]) / float(components[1])
                            else:
                                print("Data error: " + text)
                                skip = True
                                break
                            if best is None or factor > best:
                                best = factor
                                best_bookie = bookie
            if best is None:
                skip = True
                break
            factors.append(best)
            factor_bookies.append(best_bookie)
        if not skip:
            print(factor_bookies)
            result, gain = arbitrage(factors)
            show_result(factors, result, value)
            last_distribution = result
            last_bookies = factor_bookies
    elif command == "f" or command == "follow":
        index = len(last_results) - int(arguments[1])
        if index >= 0:
            driver.get(last_results[index][5])
        else:
            print("No such result")
    elif command == "back":
        driver.get(last_overview)
    elif command == "amount":
        if last_distribution:
            print(last_bookies)
            if len(arguments) == 2:
                total = float(arguments[1])
            elif len(arguments) == 3 and int(arguments[1]) <= len(last_distribution):
                total = float(arguments[2]) / last_distribution[int(arguments[1]) - 1]
            else:
                print("Incorrect arguments")
                skip = True
            if not skip:
                result = last_distribution.copy()
                for i in range(len(result)):
                    result[i] = round(result[i] * total, 2)
                print(result)
    else:
        print("Unknown command: " + command)
