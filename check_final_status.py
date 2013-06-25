from pymongo import *

MONGO_IP = 'localhost:27017'
con = Connection(MONGO_IP)
db = con['PSP']
col = db['pnr_details']

class Check_final_status:
    def __init__(self):
        pass

    def check_and_update(self):
        # Final status can be WL,RAC,CNF,Can/Mod
        # Variations of coach number: H1,B11,S1,S12,SK2,G7,SE1,C1,AB,ABE,AB1,ABE1,HA,HA1. If prefixed by "R" means RAC
        """ Various cases and how API returns value based on them
            1. Ticket is confirmed from the beginning -> { "status" : "CNF", "seat_number" : "S8 , 61,GN" }, { "status" : "B6 , 63", "seat_number" : "B6 , 63,GN" }
            2. Ticket is waiting initially but gets confirmed before preparation of chart -> {"status" : "Confirmed",   "seat_number" : "W/L  55,GNWL" }
            3. Ticket is waiting initially and gets confirmed after chart preparation -> { "status" : "B1 , 17", "seat_number" : "W/L 46,HO" }
            4. Ticket is waiting initially and gets RAC after chart preparation -> {    "status" : "RS13 23",   "seat_number" : "W/L 287,GNWL" }
            5. Ticket is waiting initially and remains waiting even after chart preparation -> {"status" : "W/L  17",   "seat_number" : "W/L  80,GNWL" }
            6. Ticket is RAC initially but gets confirmed before preparation of chart -> { "status" : "Confirmed",     "seat_number" : "RAC  14,GNWL" }
            7. Ticket is RAC initially and gets confirmed after chart preparation -> {"status" : "S2 , 35",   "seat_number" : "RAC  8,RLGN" }
            8. Ticket is RAC initially and remains RAC even after chart preparation -> "status" : {"status" : "RS6  31",    "seat_number" : "RAC  44,GNWL" }
            9. Ticket is CNF/WL/RAC initially and is cancelled/modifed before chart preparation -> { "status" : "Can/Mod",   "seat_number" : "B1 , 22,GN" }
            10. Ticket is CNF/WL/RAC initially and is cancelled/modifed after chart preparation -> { "status" : "Can/Mod", "seat_number" : "CNF ,GN" }
        """
        # Update the final status as follows -> WL, RAC, CNF

	print 'Checking and updating the final_status'
        # final_status : WL   initial_status : WL      Case:5
        res = col.update({'chart_prepared':True, 'final_status':{'$exists':False}, 'passenger':{'$elemMatch':{'status':{'$regex':'^W\/L'}, 'seat_number':{'$regex':'^W\/L'} } }},{'$set':{'final_status':'wl'}},multi=True)
	print 'Case 5 : count is ',res

        # final_status : RAC   initial_status: WL,RAC    Case:4,8
        res = col.update({'chart_prepared':True, 'final_status':{'$exists':False}, 'passenger.status':{'$regex':'^R' }},{'$set':{'final_status':'rac'}},multi=True)

        # final_status : CNF     initial_status: WL      Case: 2
        res = col.update({'chart_prepared':False, 'final_status':{'$exists':False}, 'passenger':{'$elemMatch':{'status':'Confirmed', 'seat_number':{'$regex':'^W\/L'}}} },{'$set':{'final_status':'cnf'}},multi=True)

        # final_status : CNF     initial_status: WL      Case: 3
        res = col.update({'chart_prepared':True, 'final_status':{'$exists':False}, 'passenger':{'$elemMatch':{'$and':[{'status':{'$regex':'^(?!Can)'}},{'status':{'$regex':'^[^RW]'}}],'seat_number':{'$regex':'^W\/L'}}}},{'$set':{'final_status':'cnf'}},multi=True)

        # final_status : CNF     initial_status: RAC    Case: 6
        res = col.update({'chart_prepared':False, 'final_status':{'$exists':False}, 'passenger':{'$elemMatch':{'status':'Confirmed', 'seat_number':{'$regex':'^RAC.'}} }},{'$set':{'final_status':'cnf'}},multi=True)

        # final_status : CNF     initial_status: RAC    Case: 7
        res = col.update({'chart_prepared':True, 'final_status':{'$exists':False}, 'passenger':{'$elemMatch':{'$and':[{'status':{'$regex':'^(?!Can)'}},{'status':{'$regex':'^[^RW]'}}],'seat_number':{'$regex':'^RAC'}}}},{'$set':{'final_status':'cnf'}},multi=True)

        """
        Cases Ignored: When seat availabilty of any day shows as WL/AVAILABLE then what happens?
        """

if __name__ == "__main__":
    final_status_updater = Check_final_status() 
    final_status_updater.check_and_update()
