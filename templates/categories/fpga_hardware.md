### Category: FPGA, Hardware Design, and Embedded Systems

Tasks involving FPGA development, digital circuit design, embedded firmware, hardware description languages, and low-level system programming.

**The examples below are for inspiration only. Be creative and design your own unique task!**

**Task Pattern Ideas**:

*FPGA/Digital Design:*
- Verilog/SystemVerilog module implementation
- Digital signal processing on FPGA (filters, FFT, OFDM transceiver)
- State machine design and optimization
- Fixed-point arithmetic implementations
- Pipeline design for timing closure
- Hardware floating-point units (custom formats like E4M3, FP8)
- Communication protocols (SPI, I2C, UART, AXI)
- Memory controller design
- Clock domain crossing handling
- Low-power design techniques

*EDA Tool Flows:*
- EDA tool scripting (TCL for Vivado, Design Compiler)
- Timing constraint development (SDC format)
- RTL simulation and verification
- IC synthesis flow automation
- Lint/CDC check scripting

*Embedded Systems:*
- Implement memory-constrained firmware (8-bit architectures)
- Binary protocol parsing and encoding for embedded devices
- Satellite/aerospace embedded systems (resource-limited environments)
- Implement routing tables with manual memory management
- Bare-metal programming without standard libraries
- Bitwise operations for hardware register manipulation
- Fixed-size buffer management and memory alignment
- Embedded file system simulation (inode, block management)

**Skills & Tools** (tag suggestions for your task):
- Core: `fpga`, `verilog`, `hardware`, `digital-design`, `embedded`
- HDL: `verilog`, `systemverilog`, `vhdl`
- EDA: `vivado`, `quartus`, `design-compiler`, `modelsim`, `iverilog`
- Embedded: `bare-metal`, `firmware`, `bitwise`, `memory-management`
- Concepts: `pipeline`, `timing`, `fsm`, `fixed-point`, `dsp`, `binary-protocol`
- Scripting: `tcl`, `python`, `c`

**Possible Input Data** (be creative with environment files!):
- Verilog/SystemVerilog source files
- Testbench files with test vectors
- Timing constraint files (SDC, XDC)
- Synthesis scripts (TCL)
- Binary protocol specifications
- Memory layout definitions
- Embedded system command sequences
- Satellite telemetry data packets
- Hardware register definitions
- Resource constraint specifications (memory limits, no heap)
- Design specifications (PDF, markdown)

**Verification Approaches**:
- Simulation waveform matching
- Synthesis report analysis (resource usage, timing)
- Timing closure verification (setup/hold margins)
- Functional correctness on test vectors
- Binary output matching expected bytes
- Memory usage within constraints
- No forbidden operations (no malloc, no float)
- Protocol compliance verification
- Code coverage metrics

**Remember**: Hardware and embedded tasks require attention to resource constraints, timing, bit-level correctness, and proper coding styles. Test both functionality and constraints (memory, timing, power)!
