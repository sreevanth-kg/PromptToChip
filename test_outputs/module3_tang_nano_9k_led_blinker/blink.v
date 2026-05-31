module blink (
    input wire clk,
    output reg [5:0] led
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

        led <= {5'b11111, ~blink_state};
    end
endmodule
