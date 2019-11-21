class alert:
    def __init__(self, alertJson):
        self.detailKey = alertJson["detailKey"]
        self.eventDescription = alertJson["eventDescription"]
        self.features = []
        super().__init__()