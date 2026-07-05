// Automatically generated C++ file
//
// To build with Digital Mars C++ Compiler:
//
//    dmc -mn -WD dpwm.cpp kernel32.lib

#include <cmath>

double  Ts, // switching period
        D;  // duty cycle

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
#undef PWM
#undef Sawtooth

extern "C" __declspec(dllexport) void dpwm(void **opaque, double t, union uData *data)
{
   double &PWM      = data[0].d; // PWM output
   double &Sawtooth = data[1].d; // Sawtooth output

// Implement module evaluation code here:
      Ts= 10e-6;
      D= 0.6;

      Sawtooth= t/Ts - floor(t/Ts); // sawtooth waveform generation

      if (D>Sawtooth) {PWM= 15;}
      else {PWM=0;}
}


