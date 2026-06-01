// Automatically generated C++ file on Fri Jan 26 11:11:41 2024
//
// To build with Digital Mars C++ Compiler:
//
//    dmc -mn -WD buck_controller.cpp kernel32.lib

#include <cmath>

double
Ts,                     // switching period
D,                      // duty cycle
Sawtooth,               // sawtooth waveform
PWM,                    // pwm output
yk=0, yk_1=0, yk_2=0;   // output voltage samples

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
#undef out4

extern "C" __declspec(dllexport) void buck_controller(void **opaque, double t, union uData *data)
{
   double  in0  = data[ 0].d; // input
   double  in1  = data[ 1].d; // input
   double  in2  = data[ 2].d; // input
   double  in3  = data[ 3].d; // input
   double  in4  = data[ 4].d; // input
   double &out0 = data[5].d; // output
   double &out1 = data[6].d; // output
   double &out2 = data[7].d; // output
   double &out3 = data[8].d; // output
   double &out4 = data[9].d; // output

// Implement module evaluation code here:


      Ts= 5e-6; //200 kHz switching frequency
      D= 0.56;

      Sawtooth= t/Ts - floor(t/Ts); // sawtooth waveform generation

      if (D>Sawtooth) {PWM= 15;}    // PWM signal generation
      else {PWM= 0;}

      // sampling
      if ((in1>0.999)&&(in1<=1.001)) { yk_2= yk_1;
                                       yk_1= yk;
                                       yk=in0;}
      // outputs
      out0= yk;
      out1= yk_1;
      out2= yk_2;
      out3= PWM;
      out4= Sawtooth;


}
