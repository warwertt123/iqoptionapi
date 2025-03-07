# python
from iqoptionapi.api import IQOptionAPI
import iqoptionapi.constants as OP_code
import threading
import time
import logging
import operator
import datetime
from collections import defaultdict
from iqoptionapi.expiration import get_expiration_time
from datetime import datetime,timedelta

 
def nested_dict(n, type):
    if n == 1:
        return defaultdict(type)
    else:
        return defaultdict(lambda: nested_dict(n-1, type))


class IQ_Option:
    __version__ = "3.9.5"

    def __init__(self, email, password):
        self.size = [1, 5, 10, 15, 30, 60, 120, 300, 600, 900, 1800,
                     3600, 7200, 14400, 28800, 43200, 86400, 604800, 2592000]
        self.email = email
        self.password = password
        self.suspend = 0.5
        self.thread = None
        self.subscribe_candle = []
        self.subscribe_candle_all_size = []
        self.subscribe_mood = []
        # for digit
        self.get_realtime_strike_list_temp_data = {}
        self.get_realtime_strike_list_temp_expiration = 0
        #
        self.max_reconnect = 5
        self.connect_count = 0
        # --start
        self.connect()
        # self.update_ACTIVES_OPCODE() this auto function delay too long
        self.get_balance_id()
 # --------------------------------------------------------------------------

    def get_server_timestamp(self):
        return self.api.timesync.server_timestamp

    def set_max_reconnect(self, number):
        self.max_reconnect = number

    def connect(self):
        while True:
            try:
                self.api.close()
            except:
                pass
                #logging.error('**warning** self.api.close() fail')
            if self.connect_count < self.max_reconnect:
                self.api = IQOptionAPI(
                    "iqoption.com", self.email, self.password)
                check = None
                try:
                    check = self.api.connect()
                except:
                    logging.error('**error** connect() fail')
                if check == True:
                    # -------------reconnect subscribe_candle
                    try:
                        for ac in self.subscribe_candle:
                            sp = ac.split(",")
                            self.start_candles_one_stream(sp[0], sp[1])
                    except:
                        pass
                    # -----------------
                    try:
                        for ac in self.subscribe_candle_all_size:
                            self.start_candles_all_size_stream(ac)
                    except:
                        pass
                    # -------------reconnect subscribe_mood
                    try:
                        for ac in self.subscribe_mood:
                            self.start_mood_stream(ac)
                    except:
                        pass
                    
                    #---------for async get name: "position-changed", microserviceName
                    self.api.setOptions(1,True)     
                    self.api.subscribe_position_changed("position-changed","multi-option",2)
                    self.api.subscribe_position_changed("trading-fx-option.position-changed","fx-option",3)
                    self.api.subscribe_position_changed("position-changed","crypto",4)
                    self.api.subscribe_position_changed("position-changed","forex",5)
                    self.api.subscribe_position_changed("digital-options.position-changed","digital-option",6)
                    self.api.subscribe_position_changed("position-changed","cfd",7)
                
                    break
                time.sleep(self.suspend*2)
                self.connect_count = self.connect_count+1
            else:
                logging.error(
                    '**error** reconnect() too many time please look log file')
                exit(1)

    def check_connect(self):
        # True/False
        idle_time=abs(self.api.timesync.server_timestamp-time.time())
        if idle_time>6:
            return False
        else:
            return True
        # wait for timestamp getting

# _________________________UPDATE ACTIVES OPCODE_____________________
    def get_all_ACTIVES_OPCODE(self):
        return OP_code.ACTIVES

    def update_ACTIVES_OPCODE(self):
        # update from binary option
        self.get_ALL_Binary_ACTIVES_OPCODE()
        #crypto /dorex/cfd
        self.instruments_input_all_in_ACTIVES()
        dicc = {}
        for lis in sorted(OP_code.ACTIVES.items(), key=operator.itemgetter(1)):
            dicc[lis[0]] = lis[1]
        OP_code.ACTIVES = dicc
    def get_name_by_activeId(self,activeId):
        info=self.get_financial_information(activeId)
        try:
            return info["msg"]["data"]["active"]["name"]
        except:
            return None
    def get_financial_information(self,activeId):
        self.api.financial_information=None
        self.api.get_financial_information(activeId)
        while self.api.financial_information==None:
            pass
        return self.api.financial_information
    def get_instruments(self,type):
        #type="crypto"/"forex"/"cfd"
        time.sleep(self.suspend)
        self.api.instruments = None
        while self.api.instruments == None:
            try:
                self.api.get_instruments(type)
                start = time.time()
                while self.api.instruments == None and time.time()-start < 10:
                    pass
            except:
                logging.error('**error** api.get_instruments need reconnect')
                self.connect()
        return self.api.instruments

    def instruments_input_to_ACTIVES(self, type):
        instruments=self.get_instruments(type)
        for ins in instruments["instruments"]:
            OP_code.ACTIVES[ins["id"]] = ins["active_id"]
       

    def instruments_input_all_in_ACTIVES(self):
        self.instruments_input_to_ACTIVES("crypto")
        self.instruments_input_to_ACTIVES("forex")
        self.instruments_input_to_ACTIVES("cfd")

    def get_ALL_Binary_ACTIVES_OPCODE(self):
        init_info = self.get_all_init()
        for i in init_info["result"]["binary"]["actives"]:
            OP_code.ACTIVES[(init_info["result"]["binary"]
                             ["actives"][i]["name"]).split(".")[1]] = int(i)

# _________________________self.api.get_api_option_init_all() wss______________________
    def get_all_init(self):

        while True:
            self.api.api_option_init_all_result = None
            while True:
                try:
                    self.api.get_api_option_init_all()
                    break
                except:
                    logging.error('**error** get_all_init need reconnect')
                    self.connect()
                    time.sleep(5)
            start = time.time()
            while True:
                if time.time()-start > 30:
                    logging.error('**warning** get_all_init late 30 sec')
                    break
                try:
                    if self.api.api_option_init_all_result != None:
                        break
                except:
                    pass
            try:
                if self.api.api_option_init_all_result["isSuccessful"] == True:
                    return self.api.api_option_init_all_result
            except:
                pass
    def get_all_init_v2(self):
        self.api.api_option_init_all_result_v2 = None

        self.api.get_api_option_init_all_v2()
        start_t=time.time()
        while self.api.api_option_init_all_result_v2==None:
            if time.time()-start_t>=30:
                logging.error('**warning** get_all_init_v2 late 30 sec')
                return None
        return self.api.api_option_init_all_result_v2

        # return OP_code.ACTIVES
#------- chek if binary/digit/cfd/stock... if open or not

    def get_all_open_time(self):
        #for binary option turbo and binary
        OPEN_TIME=nested_dict(3, dict)
        binary_data=self.get_all_init_v2()
        binary_list=["binary","turbo"]
        for option in binary_list:
            for actives_id in binary_data[option]["actives"]:
                active=binary_data[option]["actives"][actives_id]
                name=str(active["name"]).split(".")[1]
                OPEN_TIME[option][name]["open"]=active["enabled"]
                
        #for digital
        digital_data=self.get_digital_underlying_list_data()["underlying"]
        for digital in digital_data:
            name=digital["underlying"]
            schedule=digital["schedule"]
            OPEN_TIME["digital"][name]["open"]=False
            for schedule_time in schedule:
                start=schedule_time["open"]
                end=schedule_time["close"]
                if start<time.time()<end:
                        OPEN_TIME["digital"][name]["open"]=True


        #for OTHER
        instrument_list=["cfd","forex","crypto"]
        for instruments_type in instrument_list:
            ins_data=self.get_instruments(instruments_type)["instruments"]
            for detail in ins_data:
                name=detail["name"]
                schedule=detail["schedule"]
                OPEN_TIME[instruments_type][name]["open"]=False
                for schedule_time in schedule:
                    start=schedule_time["open"]
                    end=schedule_time["close"]
                    if start<time.time()<end:
                            OPEN_TIME[instruments_type][name]["open"]=True


                


        return OPEN_TIME
                    
       

# --------for binary option detail

    def get_binary_option_detail(self):
        detail = nested_dict(2, dict)
        init_info = self.get_all_init()
        for actives in init_info["result"]["turbo"]["actives"]:
            name = init_info["result"]["turbo"]["actives"][actives]["name"]
            name = name[name.index(".")+1:len(name)]
            detail[name]["turbo"] = init_info["result"]["turbo"]["actives"][actives]

        for actives in init_info["result"]["binary"]["actives"]:
            name = init_info["result"]["binary"]["actives"][actives]["name"]
            name = name[name.index(".")+1:len(name)]
            detail[name]["binary"] = init_info["result"]["binary"]["actives"][actives]
        return detail

    def get_all_profit(self):
        all_profit = nested_dict(2, dict)
        init_info = self.get_all_init()
        for actives in init_info["result"]["turbo"]["actives"]:
            name = init_info["result"]["turbo"]["actives"][actives]["name"]
            name = name[name.index(".")+1:len(name)]
            all_profit[name]["turbo"] = (
                100.0-init_info["result"]["turbo"]["actives"][actives]["option"]["profit"]["commission"])/100.0

        for actives in init_info["result"]["binary"]["actives"]:
            name = init_info["result"]["binary"]["actives"][actives]["name"]
            name = name[name.index(".")+1:len(name)]
            all_profit[name]["binary"] = (
                100.0-init_info["result"]["binary"]["actives"][actives]["option"]["profit"]["commission"])/100.0
        return all_profit

# ----------------------------------------


# ______________________________________self.api.getprofile() https________________________________


    def get_profile(self):
        while True:
            try:
                respon = self.api.getprofile().json()
                time.sleep(self.suspend)
                if respon["isSuccessful"] == True:
                    return respon
            except:
                logging.error('**error** get_profile try reconnect')
                self.connect()

    def get_balance_id(self):
        self.api.profile.balance_id = None
        while True:
            try:
                respon = self.get_profile()
                self.api.profile.balance_id = respon["result"]["balance_id"]
                break
            except:
                logging.error('**error** get_balance()')

            time.sleep(self.suspend)
        return self.api.profile.balance

    def get_balance(self):
        self.api.profile.balance = None
        while True:
            try:
                respon = self.get_profile()
                self.api.profile.balance = respon["result"]["balance"]
                break
            except:
                logging.error('**error** get_balance()')

            time.sleep(self.suspend)
        return self.api.profile.balance

    def get_balances(self):
        # self.api.profile.balance=None
        while True:
            try:
                respon = self.get_profile()
                self.api.profile.balances = respon["result"]["balances"]
                break
            except:
                logging.error('**error** get_balances()')
                pass
            time.sleep(self.suspend)
        return self.api.profile.balances

    def get_balance_mode(self):
        # self.api.profile.balance_type=None
        while True:
            try:
                respon = self.get_profile()
                self.api.profile.balance_type = respon["result"]["balance_type"]
                break
            except:
                logging.error('**error** get_balance_mode()')
                pass
            time.sleep(self.suspend)
        if self.api.profile.balance_type == 1:
            return "REAL"
        elif self.api.profile.balance_type == 4:
            return "PRACTICE"

    def change_balance(self, Balance_MODE):
        real_id = None
        practice_id = None
        while True:
            try:
                self.get_balances()
                for accunt in self.api.profile.balances:
                    if accunt["type"] == 1:
                        real_id = accunt["id"]
                    if accunt["type"] == 4:
                        practice_id = accunt["id"]
                break
            except:
                logging.error('**error** change_balance()')
                pass
        while self.get_balance_mode() != Balance_MODE:
            if Balance_MODE == "REAL":
                self.api.changebalance(real_id)
            elif Balance_MODE == "PRACTICE":
                self.api.changebalance(practice_id)
            else:
                logging.error("ERROR doesn't have this mode")
                exit(1)
# ________________________________________________________________________
# _______________________        CANDLE      _____________________________
# ________________________self.api.getcandles() wss________________________

    def get_candles(self, ACTIVES, interval, count, endtime):
        self.api.candles.candles_data = None
        while True:
            try:
                self.api.getcandles(
                    OP_code.ACTIVES[ACTIVES], interval, count, endtime)
                while self.check_connect and self.api.candles.candles_data == None:
                    pass
                if self.api.candles.candles_data != None:
                    break
            except:
                logging.error('**error** get_candles need reconnect')
                self.connect()

        return self.api.candles.candles_data
#######################################################
# ______________________________________________________
# _____________________REAL TIME CANDLE_________________
# ______________________________________________________
#######################################################

    def start_candles_stream(self, ACTIVE, size, maxdict):

        if size == "all":
            for s in self.size:
                self.full_realtime_get_candle(ACTIVE, s, maxdict)
                self.api.real_time_candles_maxdict_table[ACTIVE][s] = maxdict
            self.start_candles_all_size_stream(ACTIVE)
        elif size in self.size:
            self.api.real_time_candles_maxdict_table[ACTIVE][size] = maxdict
            self.full_realtime_get_candle(ACTIVE, size, maxdict)
            self.start_candles_one_stream(ACTIVE, size)

        else:
            logging.error(
                '**error** start_candles_stream please input right size')

    def stop_candles_stream(self, ACTIVE, size):
        if size == "all":
            self.stop_candles_all_size_stream(ACTIVE)
        elif size in self.size:
            self.stop_candles_one_stream(ACTIVE, size)
        else:
            logging.error(
                '**error** start_candles_stream please input right size')

    def get_realtime_candles(self, ACTIVE, size):
        if size == "all":
            try:
                return self.api.real_time_candles[ACTIVE]
            except:
                logging.error(
                    '**error** get_realtime_candles() size="all" can not get candle')
                return False
        elif size in self.size:
            try:
                return self.api.real_time_candles[ACTIVE][size]
            except:
                logging.error(
                    '**error** get_realtime_candles() size='+str(size)+' can not get candle')
                return False
        else:
            logging.error(
                '**error** get_realtime_candles() please input right "size"')

    def get_all_realtime_candles(self):
        return self.api.real_time_candles
################################################
# ---------REAL TIME CANDLE Subset Function---------
################################################
# ---------------------full dict get_candle-----------------------

    def full_realtime_get_candle(self, ACTIVE, size, maxdict):
        candles = self.get_candles(
            ACTIVE, size, maxdict, self.api.timesync.server_timestamp)
        for can in candles:
            self.api.real_time_candles[str(
                ACTIVE)][int(size)][can["from"]] = can

# ------------------------Subscribe ONE SIZE-----------------------
    def start_candles_one_stream(self, ACTIVE, size):
        if (str(ACTIVE+","+str(size)) in self.subscribe_candle) == False:
            self.subscribe_candle.append((ACTIVE+","+str(size)))
        start = time.time()
        self.api.candle_generated_check[str(ACTIVE)][int(size)] = {}
        while True:
            if time.time()-start > 20:
                logging.error(
                    '**error** start_candles_one_stream late for 20 sec')
                return False
            try:
                if self.api.candle_generated_check[str(ACTIVE)][int(size)] == True:
                    return True
            except:
                pass
            try:

                self.api.subscribe(OP_code.ACTIVES[ACTIVE], size)
            except:
                logging.error('**error** start_candles_stream reconnect')
                self.connect()
            time.sleep(1)

    def stop_candles_one_stream(self, ACTIVE, size):
        if ((ACTIVE+","+str(size)) in self.subscribe_candle) == True:
            self.subscribe_candle.remove(ACTIVE+","+str(size))
        while True:
            try:
                if self.api.candle_generated_check[str(ACTIVE)][int(size)] == {}:
                    return True
            except:
                pass
            self.api.candle_generated_check[str(ACTIVE)][int(size)] = {}
            self.api.unsubscribe(OP_code.ACTIVES[ACTIVE], size)
            time.sleep(self.suspend*10)
# ------------------------Subscribe ALL SIZE-----------------------

    def start_candles_all_size_stream(self, ACTIVE):
        self.api.candle_generated_all_size_check[str(ACTIVE)] = {}
        if (str(ACTIVE) in self.subscribe_candle_all_size) == False:
            self.subscribe_candle_all_size.append(str(ACTIVE))
        start = time.time()
        while True:
            if time.time()-start > 20:
                logging.error('**error** fail '+ACTIVE +
                              ' start_candles_all_size_stream late for 10 sec')
                return False
            try:
                if self.api.candle_generated_all_size_check[str(ACTIVE)] == True:
                    return True
            except:
                pass
            try:
                self.api.subscribe_all_size(OP_code.ACTIVES[ACTIVE])
            except:
                logging.error(
                    '**error** start_candles_all_size_stream reconnect')
                self.connect()
            time.sleep(1)

    def stop_candles_all_size_stream(self, ACTIVE):
        if (str(ACTIVE) in self.subscribe_candle_all_size) == True:
            self.subscribe_candle_all_size.remove(str(ACTIVE))
        while True:
            try:
                if self.api.candle_generated_all_size_check[str(ACTIVE)] == {}:
                    break
            except:
                pass
            self.api.candle_generated_all_size_check[str(ACTIVE)] = {}
            self.api.unsubscribe_all_size(OP_code.ACTIVES[ACTIVE])
            time.sleep(self.suspend*10)
# ---------------------------------------------------------------------


################################################
################################################
# -----------------------------------------------

# -----------------traders_mood----------------------

    def start_mood_stream(self, ACTIVES):
        if ACTIVES in self.subscribe_mood == False:
            self.subscribe_mood.append(ACTIVES)

        while True:
            self.api.subscribe_Traders_mood(OP_code.ACTIVES[ACTIVES])
            try:
                self.api.traders_mood[OP_code.ACTIVES[ACTIVES]]
                break
            except:
                time.sleep(5)

    def stop_mood_stream(self, ACTIVES):
        if ACTIVES in self.subscribe_mood == True:
            del self.subscribe_mood[ACTIVES]
        self.api.unsubscribe_Traders_mood(OP_code.ACTIVES[ACTIVES])

    def get_traders_mood(self, ACTIVES):
        # return highter %
        return self.api.traders_mood[OP_code.ACTIVES[ACTIVES]]

    def get_all_traders_mood(self):
        # return highter %
        return self.api.traders_mood
##############################################################################################

    def check_win(self, id_number):
        # 'win'：win money 'equal'：no win no loose   'loose':loose money
        while True:
            try:
                listinfodata_dict = self.api.listinfodata.get(id_number)
                if listinfodata_dict["game_state"] == 1:
                    break
            except:
                pass
        self.api.listinfodata.delete(id_number)
        return listinfodata_dict["win"]

    def check_win_v2(self, id_number):
        while True:
            check, data = self.get_betinfo(id_number)
            if check:
                return data["result"]["data"][str(id_number)]["win"]
            time.sleep(self.suspend)
# -------------------get infomation only for binary option------------------------

    def get_betinfo(self, id_number):
        # INPUT:int
        while True:
            self.api.game_betinfo.isSuccessful = None
            start = time.time()
            try:
                self.api.get_betinfo(id_number)
            except:
                logging.error(
                    '**error** def get_betinfo  self.api.get_betinfo reconnect')
                self.connect()
            while self.api.game_betinfo.isSuccessful == None:
                if time.time()-start > 10:
                    logging.error(
                        '**error** get_betinfo time out need reconnect')
                    self.connect()
                    self.api.get_betinfo(id_number)
                    time.sleep(self.suspend*10)
            if self.api.game_betinfo.isSuccessful == True:
                return self.api.game_betinfo.isSuccessful, self.api.game_betinfo.dict
            else:
                return self.api.game_betinfo.isSuccessful, None
            time.sleep(self.suspend*10)

    def get_optioninfo(self, limit):
        self.api.api_game_getoptions_result = None
        self.api.get_options(limit)
        while self.api.api_game_getoptions_result == None:
            pass

        return self.api.api_game_getoptions_result


# __________________________BUY__________________________

# __________________FOR OPTION____________________________

    def buy_multi(self,price,ACTIVES,ACTION,expirations):
        self.api.buy_multi_option={}
        if len(price)==len(ACTIVES)==len(ACTION)==len(expirations):
            buy_len=len(price)
            for idx in range(buy_len):
                self.api.buyv3(price[idx], OP_code.ACTIVES[ACTIVES[idx]], ACTION[idx], expirations[idx],idx)
            while len(self.api.buy_multi_option)<buy_len:
                pass
            buy_id=[]            
            for key in sorted(self.api.buy_multi_option.keys()):
                try:
                    value=self.api.buy_multi_option[key]
                    buy_id.append(value["id"])
                except:
                    buy_id.append(None)

            return buy_id
        else:
            logging.error('buy_multi error please input all same len')
            

         
    def buy(self, price, ACTIVES, ACTION, expirations):
        self.api.buy_successful = None
        self.api.buy_id = None
        self.api.buy(price, OP_code.ACTIVES[ACTIVES], ACTION, expirations)
        start_t=time.time()
        while self.api.buy_successful == None and self.api.buy_id == None:
            if time.time()-start_t>=30:
                logging.error('**warning** buy late 30 sec')
                return False,None
             
        return self.api.buy_successful,self.api.buy_id
        

    def sell_option(self, options_ids):
        self.api.sell_option(options_ids)
        self.api.sold_options_respond = None
        while self.api.sold_options_respond == None:
            pass
        return self.api.sold_options_respond
# __________________for Digital___________________
    def get_digital_underlying_list_data(self):
        self.api.underlying_list_data=None
        self.api.get_digital_underlying()
        start_t=time.time()
        while self.api.underlying_list_data==None:
            if time.time()-start_t>=30:
                logging.error('**warning** get_digital_underlying_list_data late 30 sec')
                return None
           
        return self.api.underlying_list_data

    def get_strike_list(self, ACTIVES, duration):
        self.api.strike_list = None
        self.api.get_strike_list(ACTIVES, duration)
        ans = {}
        while self.api.strike_list == None:
            pass
        try:
            for data in self.api.strike_list["msg"]["strike"]:
                temp = {}
                temp["call"] = data["call"]["id"]
                temp["put"] = data["put"]["id"]
                ans[("%.6f" % (float(data["value"])*10e-7))] = temp
        except:
            logging.error('**error** get_strike_list read problem...')
            return self.api.strike_list, None
        return self.api.strike_list, ans

    def subscribe_strike_list(self, ACTIVE,expiration_period):
        self.api.subscribe_instrument_quites_generated(ACTIVE,expiration_period)

    def unsubscribe_strike_list(self, ACTIVE,expiration_period):
        del self.api.instrument_quites_generated_data[ACTIVE]
        self.api.unsubscribe_instrument_quites_generated(ACTIVE,expiration_period)

    def get_realtime_strike_list(self, ACTIVE, duration):
        while True:
            if not self.api.instrument_quites_generated_data[ACTIVE][duration*60]:
                pass
            else:
                break
        """
        strike_list dict: price:{call:id,put:id}
        """
        ans = {}
        now_timestamp = self.api.instrument_quites_generated_timestamp[ACTIVE][duration*60]

        while ans == {}:
            if self.get_realtime_strike_list_temp_data == {} or now_timestamp != self.get_realtime_strike_list_temp_expiration:
                raw_data, strike_list = self.get_strike_list(ACTIVE, duration)
                self.get_realtime_strike_list_temp_expiration = raw_data["msg"]["expiration"]
                self.get_realtime_strike_list_temp_data = strike_list
            else:
                strike_list = self.get_realtime_strike_list_temp_data

            profit = self.api.instrument_quites_generated_data[ACTIVE][duration*60]
            for price_key in strike_list:
                try:
                    side_data = {}
                    for side_key in strike_list[price_key]:
                        detail_data = {}
                        profit_d = profit[strike_list[price_key][side_key]]
                        detail_data["profit"] = profit_d
                        detail_data["id"] = strike_list[price_key][side_key]
                        side_data[side_key] = detail_data
                    ans[price_key] = side_data
                except:
                    pass

        return ans
    #thank thiagottjv 
    #https://github.com/Lu-Yi-Hsun/iqoptionapi/issues/65#issuecomment-513998357
    def buy_digital_spot(self, active,amount, action, duration):
        #Expiration time need to be formatted like this: YYYYMMDDHHII
        #And need to be on GMT time
       
        #Type - P or C
        if action == 'put':
            action = 'P'
        elif action=='call':
            action = 'C'
        else:
            logging.error('buy_digital_spot active error')
            return -1
        #doEURUSD201907191250PT5MPSPT
         
        exp,idx=get_expiration_time(int(self.api.timesync.server_timestamp),duration)  
       
        dateFormated = str(datetime.utcfromtimestamp(exp).strftime("%Y%m%d%H%M"))
        instrument_id = "do" + active + dateFormated + "PT" + str(duration) + "M" + action + "SPT" 
        self.api.digital_option_placed_id=None
         
        self.api.place_digital_option(instrument_id,amount)
        while self.api.digital_option_placed_id==None:
            pass

        return  self.api.digital_option_placed_id

    def buy_digital(self, amount, instrument_id):
        self.api.digital_option_placed_id=None
        self.api.place_digital_option(instrument_id,amount)
        start_t=time.time()
        while self.api.digital_option_placed_id==None:
            if time.time()-start_t>30:
                logging.error('buy_digital loss digital_option_placed_id')
                return False,None
        return  True,self.api.digital_option_placed_id
    def close_digital_option(self,position_id):
        self.api.result=None
        while self.get_async_order(position_id)==None:
            pass
        position_changed=self.get_async_order(position_id)
        self.api.close_digital_option(position_changed["id"])
        while self.api.result==None:
            pass
        return self.api.result

    def check_win_digital(self, buy_order_id):
        check, data = self.get_position(buy_order_id)
        if check:
            if data["position"]["status"] == "closed":
                return True, data["position"]["close_effect_amount"]
            else:
                return False, None
        else:
            return False, None
    
    def check_win_digital_v2(self,buy_order_id):
        order_data=self.get_async_order(buy_order_id)
        if  order_data!=None:
            if order_data["status"]=="closed":
                if order_data["close_reason"]=="expired":
                    if order_data["close_effect_amount"]==0:
                        return True,-1*max(order_data["buy_amount"],order_data["sell_amount"])
                    else:
                        return True,order_data["close_effect_amount"]-max(order_data["buy_amount"],order_data["sell_amount"])
                elif order_data["close_reason"]=="default":
                    return True,order_data["pnl_realized_enrolled"]
            else:
                return False,None
        else:
            return False,None

# ----------------------------------------------------------
# -----------------BUY_for__Forex__&&__stock(cfd)__&&__ctrpto

    def buy_order(self,
                instrument_type,instrument_id,
                side,amount,leverage,
                type,limit_price=None,stop_price=None,
                
                stop_lose_kind=None,stop_lose_value=None,
                take_profit_kind=None,take_profit_value=None,

                use_trail_stop=False,auto_margin_call=False,
                use_token_for_commission=False):
        self.api.buy_order_id = None
        self.api.buy_order(
            instrument_type=instrument_type, instrument_id=instrument_id, 
            side=side, amount=amount,leverage=leverage,
            type=type,limit_price=limit_price, stop_price=stop_price, 
            stop_lose_value=stop_lose_value, stop_lose_kind=stop_lose_kind,
            take_profit_value=take_profit_value, take_profit_kind=take_profit_kind,
            use_trail_stop=use_trail_stop, auto_margin_call=auto_margin_call,
            use_token_for_commission=use_token_for_commission
        )

        while self.api.buy_order_id == None:
            pass
        check, data = self.get_order(self.api.buy_order_id)
        while data["status"] == "pending_new":
            check, data = self.get_order(self.api.buy_order_id)
            time.sleep(1)

        if check:
            if data["status"] != "rejected":
                return True, self.api.buy_order_id
            else:
                return False, None
        else:

            return False, None
    def change_auto_margin_call(self,ID_Name,ID,auto_margin_call):
        self.api.auto_margin_call_changed_respond=None
        self.api.change_auto_margin_call(ID_Name,ID,auto_margin_call)
        while self.api.auto_margin_call_changed_respond==None:
            pass
        if self.api.auto_margin_call_changed_respond["status"]==2000:
            return True,self.api.auto_margin_call_changed_respond
        else:
            return False,self.api.auto_margin_call_changed_respond
        
    def change_order(self,ID_Name ,order_id,
                stop_lose_kind,stop_lose_value,
                take_profit_kind,take_profit_value,
                use_trail_stop,auto_margin_call):
        check=True
        if ID_Name=="position_id":
            check, order_data = self.get_order(order_id)
            position_id = order_data["position_id"]
            ID=position_id
        elif ID_Name=="order_id":
            ID=order_id
        else:
            logging.error('change_order input error ID_Name')

        if check:
            self.api.tpsl_changed_respond = None
            self.api.change_order(
                ID_Name=ID_Name,ID=ID,
                stop_lose_kind=stop_lose_kind,stop_lose_value=stop_lose_value,
                take_profit_kind=take_profit_kind,take_profit_value=take_profit_value,
                use_trail_stop=use_trail_stop)
            self.change_auto_margin_call(ID_Name=ID_Name,ID=ID,auto_margin_call=auto_margin_call)
            while self.api.tpsl_changed_respond == None:
                pass
            if self.api.tpsl_changed_respond["status"]==2000:
                return True,self.api.tpsl_changed_respond["msg"]
            else:
                return False,self.api.tpsl_changed_respond
        else:
            logging.error('change_order fail to get position_id')
            return False,None
    
    def get_async_order(self,buy_order_id):
        if buy_order_id in self.api.position_changed_data:   
            return self.api.position_changed_data[buy_order_id]
        else:
            return None
    def get_order(self, buy_order_id):
        # self.api.order_data["status"]
        # reject:you can not get this order
        # pending_new:this order is working now
        # filled:this order is ok now
        # new
        self.api.order_data = None
        self.api.get_order(buy_order_id)
        while self.api.order_data == None:
            pass
        if self.api.order_data["status"] == 2000:
            return True, self.api.order_data["msg"]
        else:
            return False, None
    def get_pending(self,instrument_type):
        self.api.deferred_orders=None
        self.api.get_pending(instrument_type)
        while self.api.deferred_orders==None:
            pass
        if self.api.deferred_orders["status"] == 2000:
            return True, self.api.deferred_orders["msg"]
        else:
            return False, None

    # this function is heavy
    def get_positions(self, instrument_type):
        self.api.positions = None
        self.api.get_positions(instrument_type)
        while self.api.positions == None:
            pass
        if self.api.positions["status"] == 2000:
            return True, self.api.positions["msg"]
        else:
            return False, None

    def get_position(self, buy_order_id):
        self.api.position = None
        check, order_data = self.get_order(buy_order_id)
        position_id = order_data["position_id"]
        self.api.get_position(position_id)
        while self.api.position == None:
            pass
        if self.api.position["status"] == 2000:
            return True, self.api.position["msg"]
        else:
            return False, None
    # this function is heavy

    def get_position_history(self, instrument_type):
        self.api.position_history = None
        self.api.get_position_history(instrument_type)
        while self.api.position_history == None:
            pass

        if self.api.position_history["status"] == 2000:
            return True, self.api.position_history["msg"]
        else:
            return False, None

    def get_position_history_v2(self, instrument_type,limit,offset,start,end):
        #instrument_type=crypto forex fx-option multi-option cfd digital-option turbo-option
        self.api.position_history_v2 = None 
        self.api.get_position_history_v2(instrument_type,limit,offset,start,end)
        while self.api.position_history_v2 == None:
            pass

        if self.api.position_history_v2["status"] == 2000:
            return True, self.api.position_history_v2["msg"]
        else:
            return False, None

    def get_available_leverages(self, instrument_type, actives):
        self.api.available_leverages = None
        self.api.get_available_leverages(
            instrument_type, OP_code.ACTIVES[actives])
        while self.api.available_leverages == None:
            pass
        if self.api.available_leverages["status"] == 2000:
            return True, self.api.available_leverages["msg"]
        else:
            return False, None

    def cancel_order(self, buy_order_id):
        self.api.order_canceled = None
        self.api.cancel_order(buy_order_id)
        while self.api.order_canceled == None:
            pass
        if self.api.order_canceled["status"] == 2000:
            return True
        else:
            return False

    def close_position(self, position_id):
        check, data = self.get_order(position_id)
        if data["position_id"] != None:
            self.api.close_position_data = None
            self.api.close_position(data["position_id"])
            while self.api.close_position_data == None:
                pass
            if self.api.close_position_data["status"] == 2000:
                return True
            else:
                return False
        else:
            return False
    def close_position_v2(self,position_id):
        while self.get_async_order(position_id)==None:
            pass
        position_changed=self.get_async_order(position_id)
        self.api.close_position(position_changed["id"])
        while self.api.close_position_data == None:
            pass
        if self.api.close_position_data["status"] == 2000:
            return True
        else:
            return False
         


    def get_overnight_fee(self, instrument_type, active):
        self.api.overnight_fee = None
        self.api.get_overnight_fee(instrument_type, OP_code.ACTIVES[active])
        while self.api.overnight_fee == None:
            pass
        if self.api.overnight_fee["status"] == 2000:
            return True, self.api.overnight_fee["msg"]
        else:
            return False, None
