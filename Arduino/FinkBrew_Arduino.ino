/* FinkBrew_Arduino.ino
=
= @author Eric Monroe
= @contact Emonroe7@gmail.com
=
=
=
=
=
======== Pins Required:
= Pins 22-33 are relays for pumps and valves.
= Pin 34 is alarm.
= 
= Ultrasonic TBD
=
=
=
=
=
=
=
=
= Commands:
= STP: Step
= TSP: Current Temperature setpoint
= HPT: HLT Process Point
= MPT: MLT Process Point
= BPT: BK Process Point
=
=  
= 
= 
= 
= 
= 
= TODO: Add timeout on disconnect
*/
#include <string.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include "SPI.h"
#include <PID_v1.h>

#define PI 3.14159
#define commX 4
#define commY 7
#define valsX 6
#define valsY commY

//=========== Constant Parameters ==============
const int maxComms = 6;
const int windowSize = 5000;	//PID PsuedoPWM window time
double boilSP, boilIn, boilOut;	//Boil PID values
double heatSP, heatIn, heatOut;	//HLT heater PID values

//=============  Object creation ===============
OneWire  ds(10);                    //OneWire devices connected to pin #10 (to change pin, change number)
DallasTemperature temp_sense(&ds);  //Extends and simplifies the OneWire library
PID boilPID (&boilIn, &boilOut, &boilSP, 1, 1, 1, DIRECT);	//PID for boil kettle heating element
PID heatPID (&heatIn, &heatOut, &heatSP, 1, 1, 1, DIRECT);	//PID for hot liquor tank element
//TODO: Need to set ouputs for heater relays



//Relay Schedule: 0 = OFF, 1 = ON, 2 = DON'T CARE (INTERPRET AS 0 FOR NOW)
//Could possibly use a bit field structure, bit <vector> or just 2 bytes if we need to save space here.
byte HLT_FILL[] =   	{1,0,1,0,1,0,0,0,0,0,0,0};  //Previously prog_uint8_t PROGMEM, not byte
byte HLT_RECIRC[] =     {1,0,0,1,1,0,0,0,0,0,0,0};
byte STRIKE_TRANS[] = 	{1,0,0,1,0,1,0,0,0,0,0,0};
byte MASH[] =       	{1,1,0,1,1,0,1,0,1,0,0,0};
byte SPARGE_IN_ON[] = 	{1,1,0,1,0,1,1,0,0,1,0,0};
//byte SPARGE_IN_OFF[]= {0,1,0,0,0,0,1,0,0,1,0,0};
//byte REFILL_HLT[] =   {1,0,1,0,1,0,0,0,0,0,0,0};  //For Refilling during boil at the moment, same as HLT_FILL
byte DRAIN_MLT[] =  	{0,1,0,0,0,0,1,0,0,0,1,0};
byte BOIL[] =       	{0,0,0,0,0,0,0,0,0,0,0,0};
byte COOL[] =       	{1,1,0,1,1,0,0,1,1,0,0,1};
byte FILL_FERM[] =      {0,1,0,0,0,0,0,1,0,0,1,0};
byte DRAIN_HLT[] =      {1,1,0,1,0,1,0,1,0,0,1,1};
byte FULL_CLOSE[] = 	{0,0,0,0,0,0,0,0,0,0,0,0};  //Same as BOIL, but makes code clearer

//DeviceAddress hlt_temp, mlt_temp, bk_temp;    // Creating 1Wire address variables
DeviceAddress hlt_temp_sense =	{0x28, 0x61, 0x22, 0x5D, 0x04, 0x00, 0x00, 0x4A};
DeviceAddress mlt_temp_sense =	{0x28, 0xB4, 0x04, 0x5D, 0x04, 0x00, 0x00, 0x01};
DeviceAddress bk_temp_sense =	{0x28, 0x13, 0xCE, 0x5C, 0x04, 0x00, 0x00, 0xC8};




//============= Steps ==============
enum STEPS {ST_MENU, 
			ST_READY,
			ST_FILL, 
			ST_STRIKE, 
			ST_MASH_IN, 
			ST_MASH, 
			ST_MASH_OUT, 
			ST_SPARGE, 
			ST_BOIL, 
			ST_STEEP, 
			ST_COOL, 
			ST_FILLFERM, 
			ST_DONE, 
			ST_DRAIN, 
			ST_DRAIN_MLT, 
			ST_DRAIN_HLT, 
			ST_CIP, 
			ST_ERROR};


//============ Com Vars ============
int curr_STP,prev_STP;
float HSP,MSP,BSP,HTP,MTP,BTP;
boolean sameStep = false;
const char* valid_Comms_In[] = {"stp","tsp","amt","alm"};

//Store commands from PI here
char commands [commY][commX];
char commVals [valsY][valsX];

//Function Declarations
void Actuate_Valves(byte[]);
void Parse_Commands(char[][commX],char[][valsX],int);
void Parse_Reply();
void Read_Sensors();
float Calc_Curr_Vol(int);	//1=HLT, 2=MLT, 3=BK, Calculates actual volume of fluid currently in tank specified.
float Calc_Goal_Vol(int, float);	//Calculate goal of final volume in a tank. 
float Calc_Fill_Percent(int, float, float);	//Convert volume transferred to percentage of goal to send to host PC



//   ######  ######## ######## ##     ## ########  
//  ##    ## ##          ##    ##     ## ##     ## 
//  ##       ##          ##    ##     ## ##     ## 
//   ######  ######      ##    ##     ## ########  
//        ## ##          ##    ##     ## ##        
//  ##    ## ##          ##    ##     ## ##        
//   ######  ########    ##     #######  ##  
void setup() {
	Serial.begin(115200);

	curr_STP = ST_READY;
	prev_STP = ST_READY;

	SPI.begin();


	// temp_sense.begin();
	
	// //Set Resolution (9 bit should be plenty)
	// temp_sense.setResolution(hlt_temp, TEMPERATURE_PRECISION);
	// temp_sense.setResolution(mlt_temp, TEMPERATURE_PRECISION);
	// temp_sense.setResolution(bk_temp, TEMPERATURE_PRECISION);
	// //Output debug msg over serial
	// Serial.print("Device 0 Resolution: ");
	// Serial.print(temp_sense.getResolution(hlt_temp_sense), DEC); 
	// Serial.println();
	// Serial.print("Device 1 Resolution: ");
	// Serial.print(temp_sense.getResolution(mlt_temp_sense), DEC); 
	// Serial.println();
	// Serial.print("Device 2 Resolution: ");
	// Serial.print(temp_sense.getResolution(bk_temp_sense), DEC); 
	// Serial.println();


	// pinMode(22, OUTPUT);    //Water pump
	// pinMode(23, OUTPUT);    //Wort pump
	// pinMode(24, OUTPUT);    //Water Supply valve
	// pinMode(25, OUTPUT);    //
	// pinMode(26, OUTPUT);    //
	// pinMode(27, OUTPUT);    //
	// pinMode(28, OUTPUT);    //
	// pinMode(29, OUTPUT);    //
	// pinMode(30, OUTPUT);    //
	// pinMode(31, OUTPUT);    //
	// pinMode(32, OUTPUT);    //Drain
	// pinMode(33, OUTPUT);    //HLT Coil output 3 way valve.
	// pinMode(34, OUTPUT);    //Alarm
	// pinMode(53, OUTPUT);    //Chip Select on MEGA for  SD card. Must be an output.
	
	// //Set pumps to off. This shouldn't be needed, but just in case. We can afford to do this here
	// digitalWrite(WATER_PUMP, LOW);
	// digitalWrite(WORT_PUMP, LOW);
}



// ##     ##    ###    #### ##    ## 
// ###   ###   ## ##    ##  ###   ## 
// #### ####  ##   ##   ##  ####  ## 
// ## ### ## ##     ##  ##  ## ## ## 
// ##     ## #########  ##  ##  #### 
// ##     ## ##     ##  ##  ##   ### 
// ##     ## ##     ## #### ##    ## 

void loop() {
	//Get input from serial
	boolean stringComplete = false;
	int i = 0;
	int j = 0;
	int c = 0;
	float currLevel = 0.0;
	float goalLevel = 0.0;

	//Sorting Command strings into the appropriate places as they come in.
	while(Serial.available() && (stringComplete == false))
	{
		char ch = Serial.read();

		if(ch == '\r')	//Full command received
		{
			//Parse input
			Parse_Commands(commands, commVals, i);
			stringComplete = true;
		}
		else if (ch == ';')
		{
			//command += ch;
			c = 0;
			i ++;
			j = 0;
		}
		else if (ch == ':')
		{
			c = 1;
			j = 0;
		}
		else
		{
			if (c == 0)
			{
				//write to commands array
				commands[i][j] = ch;
				j++;
			}
			else if (c == 1)
			{
				//write to commVals array
				commVals[i][j] = ch;
				j++;
			}
		}
	}

	//Check if step has changed between iterations
	if(prev_STP != curr_STP)
	{	sameStep = false;	}
	else
	{	sameStep = true;	}


	//Read all sensors
	Read_Sensors();


	//Act on the current step
	switch(curr_STP){
		/*
			Act on commands received
			Run PID Temperature controls
			Run fluid level controls
			

			MUST BE NON-BLOCKING
		*/

		//Do nothing
		case ST_READY:
			//Good job.
			break;

		//Always fill HLT to full during this step. Send 1.0 as fill amt to signal done.
		case ST_FILL:
			if(!sameStep){
				//change valve configuration
				Actuate_Valves(HLT_FILL);
			}

			//Calculate how full HLT is. If almost full, begin closing valves.
			break;

		//Heating water in HLT to strike temp to prep for Strike infusion (ST_MASH_IN)
		case ST_STRIKE:
			
			break;

		//Send strike water amount to the MLT. Will go to HLT_FILL after this to refill
		case ST_MASH_IN:

			break;

		//Recirculate MLT through coil in HLT. Heat HLT based on temp in MLT primarily while checking temp in HLT for overtemp
		case ST_MASH:

			break;

		//Legacy, same as ST_MASH
		case ST_MASH_OUT:

			break;

		//Sparge is Fly Sparge/Lautering
		case ST_SPARGE:

			break;

		//Boil BK. Monitor the ultrasonic sensor for foaming. Cut heat if foaming, and wait for some time. Signal to PC status of boil.
		case ST_BOIL:

			break;

		//Whirlpool stage
		case ST_STEEP:

			break;

		//Legacy. Using chill plate, so same as ST_FILLFERM
		case ST_COOL:

			break;

		//Drain through chill plate to fermenter.	
		case ST_FILLFERM:
		
			break;

		//Close all valves, turn off all heat, etc.
		case ST_DONE:

			break;

		//Drain all vessels
		case ST_DRAIN:

			break;

		//Drain MLT completely
		case ST_DRAIN_MLT:

			break;

		//Drain HLT completely
		case ST_DRAIN_HLT:

			break;

		//Run cleaning cycle
		case ST_CIP:

			break;

		//Something broke. Shutdown everything
		case ST_ERROR:

			break;
	}

	//Send current values
	//SEND ALL THE THINGS
	Parse_Reply();

	//TODO: CLEAR COMMAND ARRAYS FOR NEXT LOOP WITH MEMSET()

}



// ######## ##     ## ##    ##  ######  ######## ####  #######  ##    ##  ######  
// ##       ##     ## ###   ## ##    ##    ##     ##  ##     ## ###   ## ##    ## 
// ##       ##     ## ####  ## ##          ##     ##  ##     ## ####  ## ##       
// ######   ##     ## ## ## ## ##          ##     ##  ##     ## ## ## ##  ######  
// ##       ##     ## ##  #### ##          ##     ##  ##     ## ##  ####       ## 
// ##       ##     ## ##   ### ##    ##    ##     ##  ##     ## ##   ### ##    ## 
// ##        #######  ##    ##  ######     ##    ####  #######  ##    ##  ######  

void Parse_Commands(char comm[][commX], char vals[][valsX], int i){	//i = num_Comms
	//WTF
	/*
		Match commands received with valid commands
		--For loop with an if statement for each possible received command.
		--For loop goes through each comm value
		When a match is found, need to parse the value from vals arrays to the appropriate numeric type.
	*/
	for(int j = 0; j <= i; j++) //j = djindex
	{
		if(strcmp(comm[j],valid_Comms_In[0])==0)	//STP
		{
			//DO STUFF 1
			prev_STP = curr_STP;
			//Process current step value from vals[j] using stoi()
			curr_STP = stoi(vals[j]);
		}
		else if(strcmp(comm[j],valid_Comms_In[1])==0)	//TSP	
		{
			//DO STUFF 2
			//Process temperature set point from vals[j] using stof()

		}
		else if(strcmp(comm[j],valid_Comms_In[2])==0)	//AMT
		{
			//DO STUFF 3
			//Process amount set point from vals[j] using stof()
			//AMount of fluid to transfer, fill, or drain given the step
		}
		else if(strcmp(comm[j],valid_Comms_In[3])==0)	//ALM
		{
			//DO STUFF 4
			//Process alarm value from vals[j] using strcmp()
		}
	}
}


void Parse_Reply(){
	//Send Step, all temps, and then any relevent data dependent on step.

	return;
}


void Read_Sensors(){

	return;
}

float Calc_Curr_Vol(int tankNum){

	return 0.0;
}


float Calc_Goal_Vol(int tankNum, float currVol){

	return 0.0;
}

float Calc_Fill_Percent(int tankNum, float currVol, float goalVol){

	return 0.0;
}

void Actuate_Valves(byte schedule[]){
	/* Shut off pumps first
	 * Load the relay schedule profile into local var (maybe)
	 * Go through 3-12 and turn on or off each in relation to schedule.
	 * Actuate pump relays last.
	 */
	
	//Turn off pumps
	digitalWrite(22, LOW);
	digitalWrite(23, LOW);
	
	//Actuate valves for indicated step
	digitalWrite(24, schedule[2]);  //Water Supply
	digitalWrite(25, schedule[3]);  //
	digitalWrite(26, schedule[4]);
	//digitalWrite(27, schedule[5]);//Transistor #6 died. 
	digitalWrite(28, schedule[5]);
	digitalWrite(29, schedule[6]);
	digitalWrite(30, schedule[7]);
	digitalWrite(31, schedule[8]);
	digitalWrite(32, schedule[9]);
	digitalWrite(33, schedule[11]);
}