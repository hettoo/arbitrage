#!/usr/bin/python

import sys

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import StaleElementReferenceException

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import lxml.html

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

options = Options()
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option('useAutomationExtension', False)
driver = webdriver.Chrome(options=options)
driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": "Object.defineProperty(navigator, 'webdriver', { get: () => undefined })"})
driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.53 Safari/537.36'})
last_overview = "https://www.oddschecker.com/tennis"
driver.get(last_overview)

def get_body():
    global driver
    return lxml.html.fromstring(driver.page_source)

last_results = []
last_factors = []
last_distribution = []
last_bookies = []
exclude = []

def list_single():
    body = get_body()
    results = []
    skip = False
    in_play = False
    factors = []
    names = ()
    link = ""
    started = False
    title = ""
    titles = body.cssselect("h1")
    if titles:
        title = titles[0].text_content()
    fields = body.cssselect(".match-on td")
    for field in fields:
        c = field.attrib.get("class")
        if c is None:
            c = ""
        if "all-odds-click" in c:
            if "time" in c:
                in_play = len(field.cssselect(".in-play")) > 0
            else:
                names = field.cssselect(".fixtures-bet-name")
                for i in range(len(names)):
                    names[i] = names[i].text_content()
        elif "basket-add" in c and not skip:
            started = True
            components = field.text_content().split("/")
            if len(components) == 2:
                factor = 1 + float(components[0]) / float(components[1])
                factors.append(factor)
            else:
                skip = True
        elif "link-right" in c:
            if not skip:
                links = field.cssselect("a")
                if links:
                    link = links[0].attrib.get("href")
                result, gain = arbitrage(factors)
                if gain > 1:
                    results.append((gain, in_play, names, factors, result, "https://www.oddschecker.com/" + link, title))
            skip = False
            in_play = False
            factors = []
            link = ""
            started = False
        elif started:
            skip = True
    return results

def cmd_list(arguments):
    global last_results
    global last_overview
    last_overview = driver.current_url
    many = len(arguments) > 0 and arguments[0] == "many"
    if many:
        urls = [
            "american-football",
            "australian-rules",
            "baseball",
            "basketball",
            "boxing",
            "football",
            "handball",
            "rugby-league",
            "rugby-union",
            "snooker/world-championship",
            "tennis",
            "ufc-mma",
            "volleyball"
            ]
        results = []
        for url in urls:
            driver.get("https://www.oddschecker.com/" + url)
            results += list_single()
    else:
        results = list_single()
    results.sort(key = lambda x: (0 if x[1] else 1, x[0]))
    i = len(results)
    for gain, in_play, names, factors, result, _, title in results:
        if i != len(results):
            print()
        print("#" + str(i))
        if in_play:
            print("IN PLAY")
        if many and title:
            print(title)
        print(names)
        show_result(factors, result)
        i -= 1
    last_results = results

while True:
    try:
        line = input("> ")
    except EOFError:
        driver.close()
        quit()
    arguments = line.split(" ")
    command = arguments[0]
    if command == "c" or command == "calc":
        odds = arguments[1:]
        factors = []
        for odd in odds:
            components = odd.split("/")
            if len(components) == 1:
                factor = float(components[0])
            else:
                factor = 1 + float(components[0]) / float(components[1])
            factors.append(factor)
        result, gain = arbitrage(factors)
        show_result(factors, result)
        last_factors = factors
        last_distribution = result
        if len(last_bookies) != len(factors):
            last_bookies = []
    elif command == "l" or command == "list":
        cmd_list(arguments[1:])
    elif command == "d" or command == "details":
        body = get_body()
        items = body.cssselect(".diff-row")
        factors = []
        factor_bookies = []
        skip = False
        for item in items:
            try:
                fields = item.cssselect("td")[1:]
            except:
                print("Failed to get row")
                skip = True
                break
            best = None
            best_bookie = None
            for field in fields:
                bookie = field.attrib.get("data-bk")
                if bookie is not None and bookie not in exclude:
                    text = field.text_content()
                    if text and text != "SP":
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
            show_result(factors, result)
            last_factors = factors
            last_distribution = result
            last_bookies = factor_bookies
    elif command == "f" or command == "follow":
        index = len(last_results) - int(arguments[1])
        if index >= 0:
            driver.get(last_results[index][5])
        else:
            print("No such result")
    elif command == "b" or command == "back":
        driver.get(last_overview)
        i = len(last_results)
        for gain, in_play, names, factors, result, _ in last_results:
            if i != len(last_results):
                print()
            print("#" + str(i))
            if in_play:
                print("IN PLAY")
            print(names)
            show_result(factors, result)
            i -= 1
    elif command == "a" or command == "amount":
        if last_distribution:
            if last_bookies:
                print(last_bookies)
            skip = False
            if len(arguments) == 2:
                total = float(arguments[1])
            elif len(arguments) == 3 and int(arguments[1]) <= len(last_distribution):
                total = float(arguments[2]) / last_distribution[int(arguments[1]) - 1]
            else:
                print("Incorrect arguments")
                skip = True
            if not skip:
                values = last_distribution.copy()
                for i in range(len(values)):
                    values[i] = round(values[i] * total, 2)
                print(values)
                for i in range(len(values)):
                    values[i] = float(values[i])
                if len(values) == len(last_factors):
                    total = sum(values)
                    print("Total: " + str(total))
                    results = []
                    gains = []
                    for i in range(len(values)):
                        result = round(values[i] * factors[i], 2)
                        gains.append(result / total)
                        results.append(result)
                    print(results)
                    print(str((min(gains) - 1) * 100) + "% to " + str((max(gains) - 1) * 100) + "%")
    elif command == "p" or command == "place":
        values = arguments[1:].copy()
        for i in range(len(values)):
            values[i] = float(values[i])
        if len(values) == len(last_factors):
            total = sum(values)
            print("Total: " + str(total))
            results = []
            gains = []
            for i in range(len(values)):
                result = round(values[i] * factors[i], 2)
                gains.append(result / total)
                results.append(result)
            print(results)
            print(str((min(gains) - 1) * 100) + "% to " + str((max(gains) - 1) * 100) + "%")
    elif command == "e" or command == "exclude":
        exclude = arguments[1:]
    else:
        print("Unknown command: " + command)
