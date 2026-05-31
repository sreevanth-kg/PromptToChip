1. Short implementation note
The coder draft was validated before artifact export because the Tang Nano 9K LED flow requires deterministic Gowin CST generated from constraints.json and must match the approved plan. The returned artifacts below are generated from the verified Tang Nano 9K board package for the Gowin toolchain.

2. HDL code
File: led_pattern.v
```verilog
module led_pattern (
    input wire clk,
    output reg [5:0] led
);

    localparam integer CLOCK_HZ = 27000000;
    localparam integer STEP_CYCLES = CLOCK_HZ;

    reg [24:0] counter = 0;
    reg [1:0] step = 0;

    always @(posedge clk) begin
        if (counter == STEP_CYCLES - 1) begin
            counter <= 0;
            if (step == 2'd3) begin
                step <= 0;
            end else begin
                step <= step + 1'b1;
            end
        end else begin
            counter <= counter + 1'b1;
        end

        case (step)
            4'd0: begin
                led <= 6'b111111;
                led[2] <= 1'b0;
            end
            4'd1: begin
                led <= 6'b111111;
                led[3] <= 1'b0;
            end
            4'd2: begin
                led <= 6'b111111;
                led[4] <= 1'b0;
            end
            4'd3: begin
                led <= 6'b111111;
                led[5] <= 1'b0;
            end
            default: led <= 6'b111111;
        endcase
    end
endmodule
```

3. Constraint snippets
File: led_pattern.cst
```cst
IO_LOC "clk" 52;
IO_PORT "clk" IO_TYPE=LVCMOS33 PULL_MODE=UP;
IO_LOC "led[2]" 13;
IO_PORT "led[2]" IO_TYPE=LVCMOS18 PULL_MODE=UP DRIVE=8;
IO_LOC "led[3]" 14;
IO_PORT "led[3]" IO_TYPE=LVCMOS18 PULL_MODE=UP DRIVE=8;
IO_LOC "led[4]" 15;
IO_PORT "led[4]" IO_TYPE=LVCMOS18 PULL_MODE=UP DRIVE=8;
IO_LOC "led[5]" 16;
IO_PORT "led[5]" IO_TYPE=LVCMOS18 PULL_MODE=UP DRIVE=8;
```

4. Verification or next command
- Board: Tang Nano 9K
- Toolchain: Gowin
- Clock source: board_profile.json default clock, 27000000 Hz
- Verified mappings used: clk -> pin 52, led[2] -> pin 13, led[3] -> pin 14, led[4] -> pin 15, led[5] -> pin 16
- Rejected raw coder output reason: the Tang Nano 9K LED flow requires deterministic Gowin CST generated from constraints.json and must match the approved plan

