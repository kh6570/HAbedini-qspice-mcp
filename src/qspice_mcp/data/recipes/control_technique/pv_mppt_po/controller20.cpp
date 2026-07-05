// Automatically generated C++ file on Tue Sep 23 13:41:53 2025
//
// To build with Digital Mars C++ Compiler:
//
//    dmc -mn -WD controller20.cpp kernel32.lib

#include <cmath>

double  Ts=10e-6,         // switching period
        Dk=0, Dk_1,      // duty cycle samples
        Sawtooth,         // sawtooth wave for PWM
        vsmk=0, vsmk_1,    // sm voltage samples
        ismk=0, ismk_1,     // sm current samples
        psmk=0, psmk_1     // sm power samples

        ;


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
#undef out4
#undef in4
#undef in5
#undef in6
#undef out5
#undef out6
#undef out7
#undef out8
#undef out9
#undef out10
#undef in7
#undef in8
#undef in9
#undef in10

extern "C" __declspec(dllexport) void controller20(void **opaque, double t, union uData *data)
{
   double  in0   = data[ 0].d; // input -> sampling clock
   double  in1   = data[ 1].d; // input -> solar module voltage
   double  in2   = data[ 2].d; // input -> solar module current
   double  in3   = data[ 3].d; // input
   double  in4   = data[ 4].d; // input
   double  in5   = data[ 5].d; // input
   double  in6   = data[ 6].d; // input
   double  in7   = data[ 7].d; // input
   double  in8   = data[ 8].d; // input
   double  in9   = data[ 9].d; // input
   double  in10  = data[10].d; // input

   double &out0  = data[11].d; // output -> pwm output
   double &out1  = data[12].d; // output -> sampled sm voltage
   double &out2  = data[13].d; // output -> sampled sm current
   double &out3  = data[14].d; // output -> sampled sm power
   double &out4  = data[15].d; // output
   double &out5  = data[16].d; // output
   double &out6  = data[17].d; // output
   double &out7  = data[18].d; // output
   double &out8  = data[19].d; // output
   double &out9  = data[20].d; // output
   double &out10 = data[21].d; // output

// Implement module evaluation code here:


      Sawtooth= t/Ts - floor(t/Ts); // sawtooth waveform generation

      if (Dk>Sawtooth) {out0= 15;}
      else {out0=0;}

            // sampling process
      if ((in0>0.999)&&(in0<=1.001)) { // update current and previous samples
                                       vsmk_1=vsmk; vsmk= in1;
                                       ismk_1=ismk; ismk= in2;
                                       psmk_1=psmk; psmk=vsmk*ismk;
                                       Dk_1=Dk;





                                       if ( psmk > psmk_1 ) { if (vsmk > vsmk_1 ) Dk= Dk_1 - 0.02;

                                                              else                Dk= Dk_1 + 0.02; }


                                       else  { if (vsmk > vsmk_1 ) Dk= Dk_1 + 0.02;

                                               else                Dk= Dk_1 - 0.02; }




                                       }
      // outputs
      out1= vsmk;
      out2= ismk;
      out3= psmk;
      out4= Dk;
      out5=psmk_1;


}
