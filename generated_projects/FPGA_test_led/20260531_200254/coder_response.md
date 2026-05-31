1. Short implementation note
The coder draft was validated before artifact export because the Tang Nano 9K LED blinker flow requires deterministic Gowin CST generated from constraints.json. The returned artifacts below are generated from the verified Tang Nano 9K board package for the Gowin toolchain.

2. HDL code
File: led_blinker.v
```verilog
module led_blinker (
    input wire clk,
    output reg [0:0] led
);

    localparam integer CLOCK_HZ = 27000000;
    localparam integer HALF_PERIOD_CYCLES = CLOCK_HZ / 2;

    reg [24:0] counter = 0;
    reg blink_state = 1'b0;

    always @(posedge clk) begin
        if (counter == HALF_PERIOD_CYCLES - 1) begin
            counter <= 0;
            blink_state <= ~blink_state;
        end else begin
            counter <= counter + 1'b1;
        end

        led[0] <= ~blink_state;
    end
endmodule
```

3. Constraint snippets
File: led_blinker.cst
```cst
IO_LOC "clk" 52;
IO_PORT "clk" IO_TYPE=LVCMOS33 PULL_MODE=UP;
IO_LOC "led[0]" 10;
IO_PORT "led[0]" IO_TYPE=LVCMOS33 PULL_MODE=UP DRIVE=8;
```

4. Verification or next command
- Board: Tang Nano 9K
- Toolchain: Gowin
- Clock source: board_profile.json default clock, 27000000 Hz
- Verified mappings used: clk -> pin 52, led[0] -> pin 10
- Rejected raw coder output reason: the Tang Nano 9K LED blinker flow requires deterministic Gowin CST generated from constraints.json

