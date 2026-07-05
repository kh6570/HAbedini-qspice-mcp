// Automatically generated C++ file on Mon Feb  5 19:35:36 2024
//
// To build with Digital Mars C++ Compiler:
//
//    dmc -mn -WD dpwmcl.cpp kernel32.lib

#include <cmath>

const double
Vref= 5,           // reference voltage
Ts=5e-6,           // mosfet switching period (200 kHz)
Tsp= 1e-6,         // sampling period
Tau_z= 2.24e-5,    // compensator zero time constant
Tau_i= 2.24e-5;    // compensator gain time constant


double
Dk=0,             // current duty cycle sample
Dk_1=0,           // previous duty cycle sample
Vok=0,            // current output voltage measured sample
Vok_1=0,          // previous output voltage measured sample
Errk= Vref,       // current error sample
Errk_1=0;         // previous error sample

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
#undef Vos
#undef Vfb
#undef CLK
#undef Ds

extern "C" __declspec(dllexport) void dpwmcl(void **opaque, double t, union uData *data)
{
   double  Vfb      = data[0].d; // input
   double  CLK      = data[1].d; // input
   double &PWM      = data[2].d; // output
   double &Sawtooth = data[3].d; // output
   double &Vos      = data[4].d; // output
   double &Ds       = data[5].d; // output

// Implement module evaluation code here:

      // 10-Vpp Sawtooth waveform for PWM generation

      Sawtooth= 10*(t/Ts - floor(t/Ts));

      // digital compensator loop
      if ((CLK>0.999)&&(CLK<=1.001))  {
                                       Dk_1=   Dk ;        // save previous D sample
                                       Vok_1=  Vok;        // save previous Output Voltage sample
                                       Errk_1= Errk;       // save previous Error sample

                                       Vok=  Vfb;          // load current Output Voltage sample
                                       Errk= Vref-Vok;     // calculate current Error sample

                                       // calculate current duty cycle
                                       Dk= Dk_1 + (Tau_z+0.5*Tsp)*Errk/Tau_i - (Tau_z-0.5*Tsp)*Errk_1/Tau_i ;

                                       if (Dk>8) {Dk=8;} // Limiter
                                       if (Dk<1) {Dk=1;} // Dmax=0.8, Dmin=0.1
                                      }

      // update duty cycle PWM output

      if (Dk>Sawtooth)   {PWM= 15;}
      else               {PWM=0;}

      // show sampled output voltage and duty cycle
      Vos= Vok;
      Ds=  Dk;

}
