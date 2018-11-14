#!/usr/bin/env python3
import time
import sys
import os
import requests
import threading
from pprint import pprint
from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics


SPEED = 5 # varies from (0, inf), 1 is default speed
BRIGHTNESS = 50

def fetch_user_stocks(current_stocks):
    global BRIGHTNESS
    global SPEED
    
    request_url = 'https://kvstore.p.mashape.com/collections/stocks/items/stocks'
    response = requests.get(request_url, headers={'X-Mashape-Key': 'WBbVx5C9awmshoHyMwmMPoMsV6rLp1U3PPBjsnccQVMLGQ9vp4'})
    body = response.json()
    stocks_string = body['value']
    stocks = stocks_string.split(',')
    stocks.sort()
    stocks_set = set(stocks)

    request_url = 'https://kvstore.p.mashape.com/collections/stocks/items/brightness_speed'
    response = requests.get(request_url, headers={'X-Mashape-Key': 'WBbVx5C9awmshoHyMwmMPoMsV6rLp1U3PPBjsnccQVMLGQ9vp4'})
    body = response.json()
    brightness_speed_string = body['value']
    items = brightness_speed_string = brightness_speed_string.split(',')
    BRIGHTNESS = int(items[0])
    SPEED = float(items[1])

    stock_dict = {}
    for s in current_stocks:
        stock_dict[s.symbol] = s

    stock_rows = [StockRow(), StockRow(), StockRow()]
    new_stocks = False
    stock_list = []
    counter = 0
    for stock in stocks:
        if stock in stock_dict:
            stock_rows[counter].append(stock_dict[stock])
            stock_list.append(stock_dict[stock])
        else:
            new_stocks = True
            new_stock = Stock(stock)
            stock_rows[counter].append(new_stock)
            stock_list.append(new_stock)

        counter += 1
        if counter >= 3:
            counter = 0
    
    for stock in current_stocks:
        if stock.symbol not in stocks_set:
            new_stocks = True

    return stock_rows if new_stocks else None, stock_list


def refresh_stock_values(stock_rows, all_stocks):
    requested_stocks = ','.join([s.symbol for s in all_stocks])

    request_url = 'https://api.iextrading.com/1.0/stock/market/batch?symbols={}&types=quote&filter=latestPrice,change'.format(requested_stocks)
    response = requests.get(request_url)
    body = response.json()
    
    for row in stock_rows:
        row.dirty = True
        
        for stock in row.stocks:
            stock.value = body[stock.symbol]['quote']['latestPrice']
            stock.change = body[stock.symbol]['quote']['change']
            
        
def attributed_chars(chars, attr):
    return [(c, attr) for c in chars]


class Stock(object):
    def __init__(self, symbol):
        self.symbol = symbol
        self.value = 0.0
        self.change = 0.0

class StockRow(object):
    def __init__(self, stocks=None, position=None):
        self.stocks = stocks if stocks else []
        self.position = position if position else 0
        self.description = []
        self.dirty = True

    def append(self, stock):
        self.dirty = True
        self.stocks.append(stock)

    def clear(self):
        self.dirty = True
        self.stocks = []

    def describe(self):
        if not self.dirty:
            return self.description
        
        self.description = []
        for i, s in enumerate(self.stocks):
            self.description += attributed_chars(s.symbol + ' ', 0)
            if s.value == 0:
                self.description += attributed_chars("$0, 0%", 1)
            else:
                if s.change > 0:
                    self.description += attributed_chars("{:.2f} ▲{:.2f}%".format(s.value, round(s.change / s.value * 100, 2)), 1)
                else:
                    self.description += attributed_chars("{:.2f} ▼{:.2f}%".format(s.value, round(s.change / s.value * -100, 2)), -1)

            if i < len(self.stocks) - 1:
                self.description += attributed_chars("   ", 0)
        
        return self.description


class MatrixHandler(object):
    def __init__(self):
        self.options = RGBMatrixOptions()
        
        self.options.rows = 32
        self.options.cols = 32
        self.options.chain_length = 2
        self.options.parallel = 1
        self.options.row_address_type = 0 
        self.options.multiplexing = 0
        self.options.pwm_bits = 11
        self.options.brightness = BRIGHTNESS
        self.options.pwm_lsb_nanoseconds = 130
        self.options.led_rgb_sequence = "RGB"

        self.matrix = RGBMatrix(options = self.options)
        self.stocks = []
        self.rows = [StockRow(), StockRow(), StockRow()]

        new_rows, self.stocks = fetch_user_stocks(self.stocks)
        if new_rows is not None:
            self.rows = new_rows
        refresh_stock_values(self.rows, self.stocks)

        self.neutral_color = graphics.Color(255, 255, 255)
        self.good_color = graphics.Color(0, 255, 0)
        self.bad_color = graphics.Color(255, 0, 0)
        
    def draw_attributed_text(self, canvas, font, x_pos, y_pos, text):
        length = 0
        for character, attr in text:
            text_color = self.neutral_color
            if attr == 1:
                text_color = self.good_color
            elif attr == -1:
                text_color = self.bad_color
            
            if character == '▲':
                # draw up trianglei
                start_x = x_pos + length
                end_x = x_pos + length + 4
                start_y = y_pos - 3
                graphics.DrawLine(canvas, start_x, start_y, end_x, start_y, text_color)
                graphics.DrawLine(canvas, start_x, start_y - 1, end_x, start_y - 1, text_color)
                graphics.DrawLine(canvas, start_x + 1, start_y - 2, end_x - 1, start_y - 2, text_color)
                graphics.DrawLine(canvas, start_x + 1, start_y - 3, end_x - 1, start_y - 3, text_color)
                graphics.DrawLine(canvas, start_x + 2, start_y - 4, end_x - 2, start_y - 4, text_color)

                length += 6
                pass
            elif character == '▼':
                # draw down triangle
                start_x = x_pos + length
                end_x = x_pos + length + 4
                start_y = y_pos - 7

                graphics.DrawLine(canvas, start_x, start_y, end_x, start_y, text_color)
                graphics.DrawLine(canvas, start_x, start_y + 1, end_x, start_y + 1, text_color)
                graphics.DrawLine(canvas, start_x + 1, start_y + 2, end_x - 1, start_y + 2, text_color)
                graphics.DrawLine(canvas, start_x + 1, start_y + 3, end_x - 1, start_y + 3, text_color)
                graphics.DrawLine(canvas, start_x + 2, start_y + 4, end_x - 2, start_y + 4, text_color)

                length += 6
            else:
                length += graphics.DrawText(canvas, font, x_pos + length, y_pos, text_color, character)
        return length

    def refresh_value(self):
        refresh_stock_values(self.rows, self.stocks)
        
    def trigger_value_refresh(self):
        thread = threading.Thread(target=self.refresh_value, args=())
        thread.daemon = True
        thread.start()
        
    def refresh_stocks(self):
        new_rows, new_stocks = fetch_user_stocks(self.stocks)
        if new_rows is not None:
            self.rows = new_rows
            self.stocks = new_stocks
        
    def trigger_stocks_refresh(self):
        thread = threading.Thread(target=self.refresh_stocks, args=())
        thread.daemon = True
        thread.start()

    def run(self):
        canvas = self.matrix.CreateFrameCanvas()
        print(dir(canvas))
        font = graphics.Font()
        font.LoadFont("assets/boxxy.bdf")
        text_color = graphics.Color(255, 255, 255)

        spacing = 28

        for row in self.rows:
            row.position = canvas.width
        
        refetch_counter = 0
        fetch_value = False

        while True:
            canvas.brightness = BRIGHTNESS
            refetch_counter += 1
            
            if refetch_counter >= 60 * SPEED:
                if fetch_value:
                    self.trigger_value_refresh()
                else:
                    self.trigger_stocks_refresh()
                fetch_value = not fetch_value
                refetch_counter = 0
            
            canvas.Clear()
            
            for i, row in enumerate(self.rows):
                y_pos = (i + 1) * 10 + i
                x_pos = row.position
                
                length = self.draw_attributed_text(canvas, font, x_pos, y_pos, row.describe())
                
                row.position -= 1

                tail_position = row.position + length
                if (tail_position < canvas.width and tail_position < canvas.width - spacing):
                    wraparound_x = tail_position + spacing
                    length = self.draw_attributed_text(canvas, font, wraparound_x, y_pos, row.describe())

                if (row.position + length < 0):
                    row.position = spacing - 2

            time.sleep(0.08 / SPEED)
            canvas = self.matrix.SwapOnVSync(canvas)


if __name__ == "__main__":
    handler = MatrixHandler()

    try:
        handler.run()
    except KeyboardInterrupt:
        print("Exiting...\n")
        sys.exit(0)
