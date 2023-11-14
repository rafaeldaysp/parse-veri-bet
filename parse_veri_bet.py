from requests_html import HTMLSession
from fake_useragent import UserAgent
from bs4 import BeautifulSoup
from dataclasses import dataclass, asdict
from datetime import datetime
import pytz

def run_html_session(url, sleep_time = 15):
  ua = str(UserAgent().chrome)
  session = HTMLSession(browser_args=["--no-sandbox", "--user-agent="+ua])
  try:
    r = session.get(url)
    r.html.render(sleep = sleep_time, timeout=30)
  except Exception as e:
    print(e)
    return None

  site = BeautifulSoup(r.html.raw_html, 'html.parser')

  session.close()
  r.close()
  
  return site

def convert_to_utc_date(input_string):
  if "(" in input_string:
    format_str = "%I:%M %p ET (%m/%d/%Y)"
  else:
    format_str = "%I:%M %p ET"

  input_time = datetime.strptime(input_string, format_str)
  et_timezone = pytz.timezone("US/Eastern")
  localized_time = et_timezone.localize(input_time)
  utc_time = localized_time.astimezone(pytz.utc).isoformat()
  
  return utc_time

@dataclass
class Item:
    sport_league: str = ''     # sport as we classify it, e.g. baseball, basketball, football
    event_date_utc: str = ''   # date of the event, in UTC, ISO format
    team1: str = ''            # team 1 name
    team2: str = ''            # team 2 name
    pitcher: str = ''          # optional, pitcher for baseball
    period: str = ''           # full time, 1st half, 1st quarter and so on
    line_type: str = ''        # whatever site reports as line type, e.g. moneyline, spread, over/under
    price: str = ''            # price site reports, e.g. '-133' or '+105'
    side: str = ''             # side of the bet for over/under, e.g. 'over', 'under'
    team: str = ''             # team name, for over/under bets this will be either team name or total
    spread: float = 0.0        # for handicap and over/under bets, e.g. -1.5, +2.5
  
if __name__ == '__main__':
  while True:
    site = run_html_session('https://veri.bet/odds-picks?filter=upcoming')
    if site:
      bets_table = site.find('table', {'id': 'odds-picks'})
      if bets_table: break
  
  bets_table_rows = bets_table.find('tbody').findAll('tr', {'role': 'row'}, recursive=False)
  
  data = []
  
  for row in bets_table_rows:
    new_sport_league = row.find('h2', {'class': 'text-body'})
    if not new_sport_league:
      events_containers = row.findAll('div', {'class': 'row justify-content-md-center'})
      for container in events_containers:
        table_wrappers = container.findAll('div', {'style': 'line-height: .85rem;'})
        
        for table_wrapper in table_wrappers:
          
          table_rows = table_wrapper.find('table').find('tbody').findAll('tr', recursive=False)
          
          period_tag = table_rows[0].find('span')
          period = period_tag.text[0:period_tag.text.find('ODDS')].strip()
          
          columns_row_1 = table_rows[1].findAll('td', recursive=False)
          columns_row_2 = table_rows[2].findAll('td', recursive=False)
          columns_row_3 = table_rows[3].findAll('td', recursive=False)
          
          team1 = columns_row_1[0].text.strip()
          team2 = columns_row_2[0].text.strip()
          
          event_date = columns_row_3[0].find('span', {'class': 'badge badge-light text-wrap text-left'}).text.strip()
          
          ml_1 = columns_row_1[1].text.strip()
          ml_2 = columns_row_2[1].text.strip()
          
          spread_1_unformatted = columns_row_1[2].text.strip()
          spread_2_unformatted = columns_row_2[2].text.strip()
          
          spread_1 = spread_1_unformatted[spread_1_unformatted.find('(') + 1:spread_1_unformatted.find(')')] if 'N/A' not in spread_1_unformatted else spread_1_unformatted
          
          spread_2 = spread_2_unformatted[spread_2_unformatted.find('(') + 1:spread_2_unformatted.find(')')] if 'N/A' not in spread_2_unformatted else spread_2_unformatted
          
          over_unformatted = columns_row_1[3].text.strip()
          under_unformatted = columns_row_2[3].text.strip()
          
          over = over_unformatted[over_unformatted.find('(') + 1:over_unformatted.find(')')] if 'N/A' not in over_unformatted else over_unformatted
          
          under = under_unformatted[under_unformatted.find('(') + 1:under_unformatted.find(')')] if 'N/A' not in under_unformatted else under_unformatted
                    
          spread_for_spread_1 = float(spread_1_unformatted[0:spread_1_unformatted.find('(')].strip()) if 'N/A' not in spread_1_unformatted else 0.0
          
          spread_for_spread_2 = spread_for_spread_1 * -1
          
          spread_for_under = float(under_unformatted[0:under_unformatted.find('(')].strip().replace('U', '').replace('O', '')) if 'N/A' not in under_unformatted else 0.0
          
          spread_for_over = spread_for_under
          
          six_possible_items = [{'line_type': 'moneyline', 'price': ml_1, 'side': team1, 'team': team1, 'spread': 0.0 }, {'line_type': 'moneyline', 'price': ml_2, 'side': team2, 'team': team2, 'spread': 0.0 }, {'line_type': 'spread', 'price': spread_1, 'side': team1, 'team': team1, 'spread': spread_for_spread_1 }, {'line_type': 'spread', 'price': spread_2, 'side': team2, 'team': team2, 'spread': spread_for_spread_2}, {'line_type': 'over/under', 'price': over, 'side': 'over', 'team': team1, 'spread': spread_for_over }, {'line_type': 'over/under', 'price': under, 'side': 'under', 'team': team2, 'spread': spread_for_under}]
          
          for possible_item in six_possible_items:
            item = Item()
            item.sport_league = sport_league
            item.event_date_utc = convert_to_utc_date(event_date)
            item.team1 = team1
            item.team2 = team2
            item.period = period
            item.line_type = possible_item['line_type']
            item.price = possible_item['price']
            item.side = possible_item['side']
            item.team = possible_item['team']
            item.spread = possible_item['spread']
          
            data.append(asdict(item))
          
    else:
      sport_league = new_sport_league.text.strip()
  
  print(data)