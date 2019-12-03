import json

class EmailRequestMessage(object):
    def __init__(self, alertName, alertType, detailKey, startTime, endTime, description, recepientNames, toAddresses, ccAddresses, sites, recommendations):
        self.alertName = alertName
        self.alertType = alertType
        self.detailKey = detailKey
        self.startTime = startTime
        self.endTime = endTime
        self.description = description
        self.recepientNames = recepientNames
        self.toAddresses = toAddresses
        self.ccAddresses = ccAddresses
        self.sites = sites
        self.recommendations = recommendations
        super().__init__()

    @classmethod
    def from_alert_detail_json(cls, alert_detail):
        obj = cls( alertName=alert_detail['phenomena'],
                    alertType=alert_detail['headlineText'],
                    detailKey=alert_detail['detailKey'],
                    startTime=alert_detail['effectiveTimeLocal'],
                    endTime=alert_detail['expireTimeLocal'],
                    description=alert_detail['texts'][0]['description'],
                    recepientNames=[],
                    toAddresses=[],
                    ccAddresses=[],
                    sites=[],
                    recommendations=alert_detail['Recommendations']
                    )
        
        #add email addresses without duplicating them
        for b in alert_detail['buildings']:
            obj.sites.append({
                'site': b["Site Name"],
                'address': b["Address"],
                'city': b["City"]
            })
            if b['FM'] not in obj.recepientNames:
                obj.recepientNames.append(b['FM'])
                obj.toAddresses.append(b['FM Email'])
            
            if b['Tech'] not in obj.recepientNames:
                obj.recepientNames.append(b['Tech'])
                obj.toAddresses.append(b['Tech Email'])
            
            if (b['MSM Email'] not in obj.ccAddresses):
                obj.ccAddresses.append(b['MSM Email'])
            
        return obj


        
    