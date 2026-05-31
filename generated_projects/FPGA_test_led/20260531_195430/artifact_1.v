module blinker (
    input clk,
    output reg led = 1 // Initialize to inactive (off)
);

reg [23:0] counter = 0;

always @(posedge clk) begin
    if (counter == 24'd13_500_000 - 1) begin // Adjust for zero-based counting
        counter <= 0;
        led <= ~led; // Toggle every half second
    end else begin
        counter <= counter + 1;
    end
end

endmodule
