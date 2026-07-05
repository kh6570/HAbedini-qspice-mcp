// Automatically generated C++ file on Sun May  5 13:10:40 2024
//
// To build with Digital Mars C++ Compiler:
//
//    dmc -mn -WD controller2.cpp kernel32.lib

#include <cmath>

double Tsw,       // switching period
       Ramp,      // auxilary ramp signal
       vref= 5,
       k0= 0.65,
       w0= 2*3.1416*3.06e3,
       vok= 0,       // current output voltage sample
       vok_1= 0,   // previous output voltage sample
       ipk= 0,       // current peak current sample
       ipk_1= 0,     // previous peak current sample
       errk= vref,      // current error sample
       errk_1= 0;    // previous error sample



union uData
{
   bool b;
   char c;
   unsigned char uc;
   short s;
   unsigned short us;
   int i;
   unsigned int ui;
   float f;
   double d;
   long long int i64;
   unsigned long long int ui64;
   char *str;
   unsigned char *bytes;
};

// int DllMain() must exist and return 1 for a process to load the .DLL
// See https://docs.microsoft.com/en-us/windows/win32/dlls/dllmain for more information.
int __stdcall DllMain(void *module, unsigned int reason, void *reserved) { return 1; }

// #undef pin names lest they collide with names in any header file(s) you might include.
#undef in0
#undef in1
#undef in2
#undef in3
#undef out0
#undef out1
#undef out2
#undef out3
#undef in4
#undef in5
#undef out4
#undef out5

extern "C" __declspec(dllexport) void controller2(void **opaque, double t, union uData *data)
{
   double  in0  = data[ 0].d; // input
   double  in1  = data[ 1].d; // input
   double  in2  = data[ 2].d; // input
   double  in3  = data[ 3].d; // input
   double  in4  = data[ 4].d; // input
   double  in5  = data[ 5].d; // input
   double  fsw  = data[ 6].d; // input parameter
   double  Tsp  = data[ 7].d; // input parameter
   double &out0 = data[8].d; // output
   double &out1 = data[9].d; // output
   double &out2 = data[10].d; // output
   double &out3 = data[11].d; // output
   double &out4 = data[12].d; // output
   double &out5 = data[13].d; // output

// Implement module evaluation code here:


// in0, switching clock
// in1, inductor current
// in2, inductor peak current reference
// in3, sampling clock
// in4, output voltage sensed signal
// out0, pwm output
// out1, ramp output

            Tsw=1/fsw;
            Ramp= 0.25*(t/Tsw - floor(t/Tsw)); // auxiliary ramp generation
            out1= Ramp;

            if ((in0>0.999)&&(in0<=1.001))  out0=15; // turns on switch every switching period

            if ((in1+Ramp)>ipk)             out0=0;  // turns off switch when current > peak current ref.

            if ((in3>0.999)&&(in3<=1.001))  {
                                                vok_1 = vok;      // saves previous samples
                                                ipk_1 = ipk;
                                                errk_1= errk;

                                                vok= in4;         // reads current samples
                                                errk= vref - vok;

                                                ipk = ipk_1 + k0*(1 + w0*Tsp/2)*errk - k0*(1 - w0*Tsp/2)*errk_1;


                                             }
            out2= vok;
            out3= ipk;


}
