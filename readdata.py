#-*- coding:utf-8 -*-
import traceback
from datetime import datetime
from collections import deque

def readdatafile(fname):
    try:
        fp = open(fname, "r")
        lines = fp.readlines()
        fp.close()
        return deque(lines)
    except:
        return None

def _checkholeinfo(row):
    if row[0].isdigit() and int(row[0]) < 37:  # 웨지 때문에, 암츤 36홀 이상 뛸 일도 없을듯 ㅋ
        return True
    return False

def _parsenotdistance(item):
    shot = {}
    if item == 'H' or item =='UN':
        shot["penelty"] = item
        shot["score"] = 2
    elif item == 'OB':
        shot["penelty"] = item
        shot["score"] = 3
    elif item == 'B':
        shot["_on"] = "bunker"
    return shot

def _parseshot(row):
    shot = {"club" : row[0], "feel" : row[1], "result" : row[2], "score" : 1, "on": "fairway", "OK": False}

    if row[2] == 'C':
        shot["_on"] = "rough" 

    if len(row) == 3:
        return shot
    if row[3].isdigit():
        shot["distance"] = float(row[3])
    elif row[3] == "OK":
        shot["score"] = 2
        shot["OK"] = True
    else:
        tmp = _parsenotdistance(row[3])
        shot.update(tmp)

    if len(row) == 4:
        return shot

    if row[4] == 'OK':
        shot["score"] = 2
        shot["OK"] = True
    else:
        tmp = _parsenotdistance(row[3])
        shot.update(tmp)
    return shot

def _parseholenshots(data):
    row = data.popleft().split()
    if _checkholeinfo(row) is False:
        raise Exception('First row should be hole information')
    holeinfo = {"no" : int(row[0]), "par" : int(row[1][1:]), "shots":[], "score": 0}
    on = "fairway"
    while True:
        try:
            tmp = data.popleft()
        except:
            return holeinfo
        row = tmp.split()
        if _checkholeinfo(row):
            data.appendleft(tmp)
            return holeinfo
        shot = _parseshot(row)
        shot["on"] = on
        if "_on" in shot:
            on = shot["_on"]
        else:
            on = "fairway"
        holeinfo["score"] = holeinfo["score"] + shot["score"]
        holeinfo["shots"].append(shot)

def parsedata(data):
    try:
        parsed = {}
        # header
        #parsed["datetime"] = datetime.strptime(data.popleft().strip(), '%Y.%m.%d %H:%M')
        #parsed["club"] = data.popleft()
        #parsed["member"] = data.popleft().split()
        parsed["info"] = data.popleft()
        parsed["holes"] = []
        parsed["score"] = 0
        parsed["parts"] = []
        while len(data) > 0:
            hole = _parseholenshots(data)
            parsed["score"] = parsed["score"] + hole["score"]
            if 1 == hole["no"] % 9:
                parsed["parts"].append({"score" : hole["score"], "holes":[hole], "hscore":[hole["score"] - hole["par"]]})
            else:
                n = int((hole["no"] - 1) / 9)
                parsed["parts"][n]["score"] = parsed["parts"][n]["score"] + hole["score"]
                parsed["parts"][n]["holes"].append(hole)
                parsed["parts"][n]["hscore"].append(hole["score"] - hole["par"])

            parsed["holes"].append (hole)
        return parsed 
    except:
        traceback.print_exc()
        raise Exception("error occured before this line : " + data.popleft())

def _updateclubfeel(data, shot):
    if shot["feel"] == "A":
        data[0] = data[0] + 1
    elif shot["feel"] == "B":
        data[1] = data[1] + 1
    else:
        data[2] = data[2] + 1
    return data

def _singleshot(shots):
    data = {"UN":0, "H": 0, "OB" : 0, "D":[0,0,0], "U":[0,0,0], "DH" : 0, "DOB" : 0, "DUN":0, "BT" : 0, "WS" : 0, "SA" : 0, "P" : 0, "OK" : 0, "WOK" : 0, "I" : 0, "LI":[0,0,0], "MI" : [0,0,0], "SI" : [0,0,0], "W" : [0,0,0], "FA" : 0, "FB" : 0, "FC" : 0, "A" : 0, "B" : 0, "C" : 0, "AA" : 0, "AB" : 0, "AC": 0, "BA" : 0 , "BB" : 0, "BC" : 0, "CA" : 0, "CB" : 0, "CC" : 0, "P":[0,0,0]}
    bdata = {"B" : 0, "ESB" : 0}
    for shot in shots:
        if "penelty" in shot:
            data[shot["penelty"]] = data[shot["penelty"]] + 1
            if shot["club"] == "D":
                data["D" + shot["penelty"]] = data["D" + shot["penelty"]] + 1

        if shot["club"] in data:
            if shot["club"] in ["P", "D"]:
                data[shot["club"]] = _updateclubfeel(data[shot["club"]], shot)
            else:
                data[shot["club"]] = data[shot["club"]] + 1
        else:
            data[shot["club"]] = 1

        if shot["OK"]:
            data["OK"] = data["OK"] + 1
            if shot["club"] != "P":
                data["WOK"] = data["WOK"] + 1

        if shot["club"] in ("52", "56", "IP", "IW"):
            data["W"] = _updateclubfeel(data["W"], shot)
        elif shot["club"][0] == "I":
            if shot["club"] in ("I3", "I4"):
                data["LI"] = _updateclubfeel(data["LI"], shot)
            elif shot["club"] in ("I5", "I6", "I7"):
                data["MI"] = _updateclubfeel(data["MI"], shot)
            elif shot["club"] in ("I8", "I9"):
                data["SI"] = _updateclubfeel(data["SI"], shot)
        elif shot["club"][0] == "U" or shot["club"][0] == "W":
            data["U"] = _updateclubfeel(data["U"], shot)

        tmp = shot["result"]
        data[tmp] = data[tmp] + 1
        tmp = "F" + shot["feel"]
        data[tmp] = data[tmp] + 1
        tmp = shot["feel"] + shot["result"]
        data[tmp] = data[tmp] + 1
        if tmp in ("AA", "BB", "CC"):
            data["SA"] = data["SA"] + 1
        elif tmp in ("BA", "CB", "CA"):
            data["BT"] = data["BT"] + 1
        elif tmp in ("BC", "AB", "AC"):
            data["WS"] = data["WS"] + 1
              
        if "_on" in shot:
            if shot["_on"] == "bunker":
                bdata["B"] = bdata["B"] + 1

        if shot["on"] == "bunker":
            if "_on" not in shot or shot["_on"] != "bunker":
                bdata["ESB"] = bdata["ESB"] + 1

    total = float(len(shots))
    rbdata = {"B" : bdata["B"] / total, "ESB" : 0 if bdata["B"] == 0 else bdata["ESB"] / float(bdata["B"])}

    rdata = {"H": 0, "OB" : 0, "B" : 0, "BT" : 0, "WS" : 0, "SA" : 0, "OK" : 0, "WOK" : 0, "I" : 0, "FA" : 0, "FB" : 0, "FC" : 0, "A" : 0, "B" : 0, "C" : 0, "AA" : 0, "AB" : 0, "AC": 0, "BA" : 0 , "BB" : 0, "BC" : 0, "CA" : 0, "CB" : 0, "CC" : 0}

    for k, v in rdata.items():
        rdata[k] = data[k] / total
    data["total"] = len(shots)

    for k in ["D", "U", "LI", "MI", "SI", "W", "P"]:
        n = sum(data[k])
        print (k, data[k][0] / n, data[k][1] / n, data[k][2] / n, n / data["total"])

    n = sum(data["D"])
    ddata = {"DH" : data["DH"] / float(n), "DOB" : data["DOB"] / float(n), "SH" : data["H"] - data["DH"], "SOB" : data["OB"] - data["DOB"]} 
    print(bdata, rbdata)
    print(data, rdata)
    print(ddata)

def analyzedata(record):
    shots = []
    for parsed in record:
        for hole in parsed['holes']:
            shots.extend (hole['shots'])
    _singleshot(shots)

if __name__ == "__main__":
    import sys
    scores = []
    record = []
    for fname in sys.argv[1:]:
        data = readdatafile(fname)
        parsed = parsedata(data)
        record.append (parsed)
        print(parsed['info'], parsed['score'], len(parsed['holes']))
        for part in parsed['parts']:
            shots = []
            print(part['score'], part['hscore'])
#            for hole in part['holes']:
#                shots.extend (hole['shots'])
#            print("singleshot")
#            _singleshot(shots)

        nscore = float(parsed['score']) / len(parsed['holes']) * 18
        scores.append (nscore)

    print (len(scores), scores)
    print (sum(scores) / len(scores))

    analyzed = analyzedata(record)

