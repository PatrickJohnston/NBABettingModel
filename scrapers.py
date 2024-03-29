from selenium import webdriver
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import time
from os.path import exists

## Scrapes regular season closing betting lines from oddsportal (consensus average) for all seasons since 2008/2009 and saves them to a csv - Make sure you have chromedriver.exe for the correct version of Chrome
## Take out the covid bubble games yourself manually
def historicOdds(A, yearStart, yearEnd):
    # A = Database(["Season","Date","Home","Away","Home ML","Away ML","Favorite","Spread","Home Spread Odds","Away Spread Odds","O/U","Over Odds","Under Odds","Home Score","Away Score"])
    seasons = []
    for i in range(yearStart, yearEnd+1):
        seasons.append(str(i) + "-" + str(i+1))
    browser = webdriver.Chrome(executable_path='chromedriver.exe')
    if (not exists("./gameUrls.csv")):
        gameUrls = []
        for season in seasons:
            browser.get("https://www.oddsportal.com/basketball/usa/nba-" + season + "/results/")
            browser.maximize_window()
            for i in range(30):
                soup = BeautifulSoup(browser.page_source, 'html.parser')
                main = soup.find(class_=" table-main")
                regSeason = False
                for row in main.find_all("tr"):
                    if ("nob-border" in row["class"]):
                        if ("Offs" in row.find("th").text or "Pre" in row.find("th").text):
                            regSeason = False
                        else:
                            regSeason = True
                    if (regSeason and "deactivate" in row["class"]):
                        gameUrls.append("https://www.oddsportal.com/" + row.find(class_="name table-participant").find("a")["href"])
                browser.find_element_by_xpath("//*[@id='pagination']/a[13]/span").click()
                time.sleep(3)
        save = {}
        save["urls"] = gameUrls
        dfFinal = pd.DataFrame.from_dict(save)
        dfFinal = dfFinal.drop_duplicates()
        dfFinal.to_csv("./gameUrls.csv", index = False)
    else:
        gameUrls = pd.read_csv('./gameUrls.csv', encoding = "ISO-8859-1")["urls"].tolist()

    counter = 0
    if (exists("./csv_data/bettingLines.csv")):
        A.initDictFromCsv("./csv_data/bettingLines.csv")
        scrapedGames = pd.read_csv('./csv_data/bettingLines.csv', encoding = "ISO-8859-1")["url"].tolist()
        for game in scrapedGames:
            gameUrls.remove(game)
    try:
        for game in gameUrls:
            browser.get(game)
            soup = BeautifulSoup(browser.page_source, 'html.parser')
            #season
            A.addCellToRow(game.split("nba-")[1].split("-")[0] + '/' + game.split("nba-")[1].split("-")[1].split("/")[0])
            #date
            A.addCellToRow(soup.find(id="col-content").find("p").text)
            #home
            A.addCellToRow(soup.find(id="col-content").find("h1").text.split(" - ")[0])
            #away
            A.addCellToRow(soup.find(id="col-content").find("h1").text.split(" - ")[1])
            #moneylines
            pinnacleFound = False
            for row in soup.find(class_="table-container").find_all("tr"):
                try:
                    sportsbook = row.find(class_="name").text
                except:
                    continue
                if (sportsbook == "Pinnacle"):
                    pinnacleFound = True
                    #home
                    A.addCellToRow(row.find_all("td")[1].text)
                    #away
                    A.addCellToRow(row.find_all("td")[2].text)
            if (not pinnacleFound):
                A.addCellToRow(np.nan)
                A.addCellToRow(np.nan)
            #spread stuff
            try:
                browser.find_element_by_xpath("//*[@id='bettype-tabs']/ul/li[4]/a/span").click()
            except:
                A.trashRow()
                continue
            time.sleep(2)
            soup = BeautifulSoup(browser.page_source, 'html.parser')
            bestPayout = -1
            for option in soup.find(id="odds-data-table").find_all("div"):
                try:
                    payout = float(option.find(class_="avg chunk-odd-payout").text.split("%")[0])
                except:
                    continue
                if (payout > bestPayout):
                    bestSpread = option
                    bestPayout = payout
            #favorite
            try:
                if ("+" in bestSpread.find("a").text):
                    A.addCellToRow(soup.find(id="col-content").find("h1").text.split(" - ")[1])
                elif ("-" in bestSpread.find("a").text):
                    A.addCellToRow(soup.find(id="col-content").find("h1").text.split(" - ")[0])
                else:
                    A.addCellToRow("Even")
            except:
                A.trashRow()
                continue
            #spread
            if ("+" in bestSpread.find("a").text):
                A.addCellToRow(bestSpread.find("a").text.split("+")[1])
            elif ("-" in bestSpread.find("a").text):
                A.addCellToRow(bestSpread.find("a").text.split("-")[1])
            else:
                A.addCellToRow(0)
            #home spread odds
            A.addCellToRow(bestSpread.find_all("a")[1].text)
            #away spread odds
            A.addCellToRow(bestSpread.find_all("a")[2].text)
            #O/U stuff
            browser.find_element_by_xpath("//*[@id='bettype-tabs']/ul/li[5]/a/span").click()
            time.sleep(2)
            soup = BeautifulSoup(browser.page_source, 'html.parser')
            bestPayout = -1
            for option in soup.find(id="odds-data-table").find_all("div"):
                try:
                    payout = float(option.find(class_="avg chunk-odd-payout").text.split("%")[0])
                except:
                    continue
                if (payout > bestPayout):
                    bestTotal = option
                    bestPayout = payout
            #O/U
            try:
                A.addCellToRow(bestTotal.find("a").text.split("+")[1])
            except:
                A.trashRow()
                continue
            #over odds
            try:
                A.addCellToRow(bestTotal.find_all("a")[1].text)
                #under odds
                A.addCellToRow(bestTotal.find_all("a")[2].text)
            except:
                A.trashRow()
                continue
            #home score
            try:
                A.addCellToRow(soup.find(class_="result").find("strong").text.split(":")[0])
            except:
                A.trashRow()
                continue
            #away score
            A.addCellToRow(soup.find(class_="result").find("strong").text.split(":")[1])
            A.addCellToRow(game)
            A.appendRow()
            counter += 1
            if (counter % 30 == 1):
                A.dictToCsv("./csv_data/bettingLines.csv")
    except:
        browser.close()
        print ("SCRAPER FAILED. RESTARTING...")
        historicOdds(A, yearStart, yearEnd)

    A.dictToCsv("./csv_data/bettingLines.csv")
    broswer.close()

## Scrapes traditional and advanced box scores from nba.com since 2005/06 season

def nbaBoxScores(A, boxScoreType = "traditional"):
    browser = webdriver.Chrome(executable_path='chromedriver.exe')
    for i in reversed(range(16)):
        browser.get("https://www.nba.com/stats/teams/boxscores-" + boxScoreType + "/?Season=2005-06&SeasonType=Regular%20Season")
        browser.maximize_window()
        browser.find_element_by_xpath("/html/body/main/div/div/div[2]/div/div/div[1]/div[1]/div/div/label/select").click()
        browser.find_element_by_xpath("/html/body/main/div/div/div[2]/div/div/div[1]/div[1]/div/div/label/select/option[" + str(i+2) + "]").click()
        time.sleep(10)
        browser.find_element_by_xpath("/html/body/main/div/div/div[2]/div/div/nba-stat-table/div[1]/div/div/select").click()
        browser.find_element_by_xpath("/html/body/main/div/div/div[2]/div/div/nba-stat-table/div[1]/div/div/select/option[1]").click()
        time.sleep(45)
        soup = BeautifulSoup(browser.page_source, 'html.parser')
        if (i == 15):
            for col in soup.find(class_="nba-stat-table").find("tr").find_all("th"):
                name = ""
                for x in col.get_text().split():
                    if (name == ""):
                        name = x
                    else:
                        name = name + " " + x
                A.addColumn(name)
        for row in soup.find(class_="nba-stat-table").find("tbody").find_all("tr"):
            for cell in row.find_all("td"):
                # if (cell.has_attr("class") and "hidden" in cell["class"]):
                #     continue
                if (len(cell.get_text().split()) == 1):
                    A.addCellToRow(cell.get_text().split()[0])
                else:
                    mu = ""
                    for x in cell.get_text().split():
                        if (mu == ""):
                            mu = x
                        else:
                            mu = mu + " " + x
                    A.addCellToRow(mu)
            A.appendRow()
    A.dictToCsv("./csv_data/" + boxScoreType + "_stats.csv")
    browser.close()
