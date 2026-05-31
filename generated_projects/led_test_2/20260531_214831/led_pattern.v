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
