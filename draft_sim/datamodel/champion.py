
# this is just a container for data, allows for ease of access and manipulation for use in integration with ui
class Champion:
    def __init__(self, name, image_path = None):
        self.name = name
        self.image_path = image_path
        #self.role = "" #role (e.g., "top", "mid", "adc", "support")
        self.champ_class = "" #class (e.g., "fighter", "mage", "assassin", "tank")
        #self.ad_percentage = 0.0
        #self.ap_percentage = 0.0
        
        self.attack_score = 0.0
        self.magic_score = 0.0
        
        self.durability_score = 0.0
        
        
        self.total_games = 0
        self.total_wins = 0
        #self.counters = [] - this should be determined via @property
        #self.synergies = [] - this should be determined via @property
        self.stats = {} #misc 

    @property
    def overall_winrate(self):
        if self.total_games < 0:
            return 0.0
        return self.total_wins / self.total_games * 100
    
    
        
    def to_dict(self): #dictionary converter for the data
        return {
            'name': self.name,
            'total_games': self.total_games,
            'total_wins': self.total_wins,
            # 'pick_rate': self.pick_rate,
            # 'ban_rate': self.ban_rate,
            'stats': self.stats
        }