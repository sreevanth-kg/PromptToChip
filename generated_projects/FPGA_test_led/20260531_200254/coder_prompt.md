
You are the local RTL coder agent for PromptToChip.

Mission:
- Convert the user's hardware request into concrete HDL-oriented output.
- Use the Tang Nano 9K board knowledge package as the source of truth.
- Do not invent package pins or constraints.
- Do not use HDMI SDA, HDMI SCL, HDMI HPD, HDMI CEC, SD DAT1, SD DAT2, or SD card detect unless a verified mapping exists in the board context.
- Prefer simple, synthesizable Verilog when the user does not specify a language.
- Include top-level port names that match verified constraints when targeting the board.
- If you provide constraints, emit Gowin CST lines only for verified mappings.
- For Tang Nano 9K / Gowin, generate .cst files only. Never emit set_property, .xdc, get_ports, PACKAGE_PIN, or Xilinx constraints.
- For an LED blinker, name files exactly: led_blinker.v and led_blinker.cst.
- Label every code block with its intended filename using a line immediately before the block, such as: File: led_blinker.v
- If the request is underspecified, produce a safe minimal implementation and state assumptions briefly.

Current project metadata:
{
  "project_name": "FPGA test led",
  "description": "Create a Tang Nano 9K LED blinker running at 1 Hz.",
  "product_goal": "",
  "board": "Tang Nano 9K",
  "hdl_language": "",
  "toolchain": "",
  "clock_frequency": "",
  "status": "discussion"
}

Recent conversation:
[
  {
    "role": "user",
    "text": "Create a Tang Nano 9K LED blinker running at 1 Hz."
  },
  {
    "role": "model",
    "text": ".NUMERIC_STD.ALL;\n\nentity led_blinker is\n    Port ( clk : in STD_LOGIC );\nend led_blinker;\n\narchitecture Behavioral of led_blinker is\n    signal counter : integer := 0;\n    signal led : std_logic := 0;\nbegin\n    process(clk)\n    begin\n        if rising_edge(clk) then\n            if counter >= (50_000_000 / 2) -1 then -- Adjust based on actual clock frequency\n                counter <= 0;\n                led <= not led;\n            else\n                counter <= counter + 1;\n            end if;\n        end if;\n    end process;\n\n    -- Assign the LED output. Replace \"led_out\" with the correct pin name.\n    assign_led: led_out <= led; \nend Behavioral;\n```\n**Note**: The actual clock frequency might vary (e.g., 50 MHz or another value). Adjust the counter threshold accordingly.\n\n3. **Constraint Snippets**:\n```tcl\n# Assuming the LED is connected to a specific pin, e.g., PIN_123\nset_location_assignment PIN_123 to led_out;\nset_false_path -from clk; # Optional: For timing analysis\n```\n\n4. **Verification**: After synthesis and programming the FPGA, monitor the LED to ensure it toggles at approximately 1 Hz. Adjust the counter value if the clock frequency differs from assumed (e.g., 50 MHz)."
  },
  {
    "role": "user",
    "text": "hi"
  },
  {
    "role": "model",
    "text": "Hello! I'm Gemma. How can I help you with your FPGA project today? If you are looking to continue with the Tang Nano 9K LED blinker we were discussing, just let me know!"
  },
  {
    "role": "user",
    "text": "yeah make it to blink"
  },
  {
    "role": "model",
    "text": "e is the summary:\n\n**What was generated**\n- A Verilog module (`artifact_1.v`) implementing a clock divider and toggle logic to achieve a 1Hz blink rate.\n- A constraints file (`artifact_2.txt`) intended to map the logic to physical pins.\n\n**Board resources used**\n- **Clock:** System clock on Pin 52.\n- **Output:** One LED on Pin 10.\n- **Logic:** A 24-bit counter to divide the 27MHz clock.\n\n**Constraints used**\n- `clk` is mapped to pin 52.\n- `led` is mapped to pin 10 using LVCMOS33.\n\n**Critique & Next Actions**\nThe work is **incomplete and contains a critical error**. While the Verilog logic is correct, the coder provided constraints using Xilinx syntax (`set_property...`) instead of the **Gowin `.cst` format** required for the Tang Nano 9K. This code will not pass the implementation stage in the Gowin EDA tool.\n\n**Next available actions:**\n1. **Fix Constraints:** Rewrite `artifact_2.txt` using correct Gowin `.cst` syntax (e.g., `IO_LOC \"clk\" 52;`).\n2. **Rename Files:** Align the filenames with the approved plan (`led_blinker.v` and `led_blinker.cst`) for better project organization.\n3. **Synthesis:** Once the constraints are fixed, you can proceed to synthesize and program the board."
  }
]

Tang Nano 9K board context:
{
  "board_id": "tang_nano_9k",
  "loaded_files": {
    "board_profile": "C:\\Users\\sreev\\Desktop\\project\\hardware_bridge\\boards\\tang_nano_9k\\board_profile.json",
    "interfaces": "C:\\Users\\sreev\\Desktop\\project\\hardware_bridge\\boards\\tang_nano_9k\\interfaces.json",
    "constraints": "C:\\Users\\sreev\\Desktop\\project\\hardware_bridge\\boards\\tang_nano_9k\\constraints.json",
    "validation_report": "C:\\Users\\sreev\\Desktop\\project\\hardware_bridge\\boards\\tang_nano_9k\\validation_report.json"
  },
  "board_profile": {
    "name": "Tang Nano 9K",
    "fpga": {
      "vendor": "Gowin",
      "family": "GW1NR",
      "part": "GW1NR-9C",
      "package": "QN88P",
      "logic_cells": 8640
    },
    "clock": {
      "default_frequency_hz": 27000000,
      "default_frequency_label": "27 MHz"
    },
    "toolchain": "gowin",
    "programming": {
      "default_programmer": "openFPGALoader",
      "toolchain": "gowin",
      "openfpgaloader_board": "tangnano9k",
      "methods": [
        "sram",
        "flash"
      ]
    }
  },
  "constraints": [
    {
      "interface": "clock",
      "signal": "clk",
      "direction": "input",
      "package_pin": "52",
      "board_net": "PIN52_XTAL_IN",
      "io_standard": "LVCMOS33",
      "frequency_hz": 27000000,
      "active_polarity": null,
      "status": "verified"
    },
    {
      "interface": "leds",
      "signal": "led[0]",
      "direction": "output",
      "package_pin": "10",
      "board_net": "PIN10_IOL15A_LED1",
      "io_standard": "LVCMOS33",
      "frequency_hz": null,
      "active_polarity": "active_low",
      "status": "verified"
    },
    {
      "interface": "leds",
      "signal": "led[1]",
      "direction": "output",
      "package_pin": "11",
      "board_net": "PIN11_IOL16B_LED2",
      "io_standard": "LVCMOS33",
      "frequency_hz": null,
      "active_polarity": "active_low",
      "status": "verified"
    },
    {
      "interface": "leds",
      "signal": "led[2]",
      "direction": "output",
      "package_pin": "13",
      "board_net": "PIN13_IOL21B_LED3",
      "io_standard": "LVCMOS33",
      "frequency_hz": null,
      "active_polarity": "active_low",
      "status": "verified"
    },
    {
      "interface": "leds",
      "signal": "led[3]",
      "direction": "output",
      "package_pin": "14",
      "board_net": "PIN14_IOL22B_LED4",
      "io_standard": "LVCMOS33",
      "frequency_hz": null,
      "active_polarity": "active_low",
      "status": "verified"
    },
    {
      "interface": "leds",
      "signal": "led[4]",
      "direction": "output",
      "package_pin": "15",
      "board_net": "PIN15_IOL25B_LED5",
      "io_standard": "LVCMOS33",
      "frequency_hz": null,
      "active_polarity": "active_low",
      "status": "verified"
    },
    {
      "interface": "leds",
      "signal": "led[5]",
      "direction": "output",
      "package_pin": "16",
      "board_net": "PIN16_IOL26B_LED6",
      "io_standard": "LVCMOS33",
      "frequency_hz": null,
      "active_polarity": "active_low",
      "status": "verified"
    },
    {
      "interface": "buttons",
      "signal": "button_s1",
      "direction": "input",
      "package_pin": "3",
      "board_net": "PIN3_IOT2A_BUTTON_S1_1V8",
      "io_standard": "LVCMOS18",
      "frequency_hz": null,
      "active_polarity": "active_low",
      "status": "verified"
    },
    {
      "interface": "buttons",
      "signal": "button_s2",
      "direction": "input",
      "package_pin": "4",
      "board_net": "PIN4_IOL5A_JTAG_SEL_S2_1V8",
      "io_standard": "LVCMOS18",
      "frequency_hz": null,
      "active_polarity": "active_low",
      "status": "verified_with_caution"
    },
    {
      "interface": "uart",
      "signal": "uart_tx",
      "direction": "output",
      "package_pin": "17",
      "board_net": "PIN17_IOB2A_FPGA_TX",
      "io_standard": "LVCMOS33",
      "frequency_hz": null,
      "active_polarity": null,
      "status": "verified"
    },
    {
      "interface": "uart",
      "signal": "uart_rx",
      "direction": "input",
      "package_pin": "18",
      "board_net": "PIN18_IOB2B_FPGA_RX",
      "io_standard": "LVCMOS33",
      "frequency_hz": null,
      "active_polarity": null,
      "status": "verified"
    },
    {
      "interface": "hdmi",
      "signal": "hdmi_clk_p",
      "direction": "output",
      "package_pin": "69",
      "board_net": "PIN69_RGB_G3/HDMI_CK_P",
      "io_standard": "LVCMOS33D",
      "frequency_hz": null,
      "active_polarity": null,
      "status": "verified"
    },
    {
      "interface": "hdmi",
      "signal": "hdmi_clk_n",
      "direction": "output",
      "package_pin": "68",
      "board_net": "PIN68_RGB_G4/HDMI_CK_N",
      "io_standard": "LVCMOS33D",
      "frequency_hz": null,
      "active_polarity": null,
      "status": "verified"
    },
    {
      "interface": "hdmi",
      "signal": "hdmi_d0_p",
      "direction": "output",
      "package_pin": "71",
      "board_net": "PIN71_RGB_R7/HDMI_D0_P",
      "io_standard": "LVCMOS33D",
      "frequency_hz": null,
      "active_polarity": null,
      "status": "verified"
    },
    {
      "interface": "hdmi",
      "signal": "hdmi_d0_n",
      "direction": "output",
      "package_pin": "70",
      "board_net": "PIN70_RGB_G2/HDMI_D0_N",
      "io_standard": "LVCMOS33D",
      "frequency_hz": null,
      "active_polarity": null,
      "status": "verified"
    },
    {
      "interface": "hdmi",
      "signal": "hdmi_d1_p",
      "direction": "output",
      "package_pin": "73",
      "board_net": "PIN73_RGB_R5/HDMI_D1_P",
      "io_standard": "LVCMOS33D",
      "frequency_hz": null,
      "active_polarity": null,
      "status": "verified"
    },
    {
      "interface": "hdmi",
      "signal": "hdmi_d1_n",
      "direction": "output",
      "package_pin": "72",
      "board_net": "PIN72_RGB_R6/HDMI_D1_N",
      "io_standard": "LVCMOS33D",
      "frequency_hz": null,
      "active_polarity": null,
      "status": "verified"
    },
    {
      "interface": "hdmi",
      "signal": "hdmi_d2_p",
      "direction": "output",
      "package_pin": "75",
      "board_net": "PIN75_RGB_R3/HDMI_D2_P",
      "io_standard": "LVCMOS33D",
      "frequency_hz": null,
      "active_polarity": null,
      "status": "verified"
    },
    {
      "interface": "hdmi",
      "signal": "hdmi_d2_n",
      "direction": "output",
      "package_pin": "74",
      "board_net": "PIN74_RGB_R4/HDMI_D2_N",
      "io_standard": "LVCMOS33D",
      "frequency_hz": null,
      "active_polarity": null,
      "status": "verified"
    },
    {
      "interface": "spi_flash",
      "signal": "flash_sck",
      "direction": "output",
      "package_pin": "59",
      "board_net": "PIN59_IOR12B_MCLK",
      "io_standard": "LVCMOS33",
      "frequency_hz": null,
      "active_polarity": null,
      "status": "verified"
    },
    {
      "interface": "spi_flash",
      "signal": "flash_cs",
      "direction": "output",
      "package_pin": "60",
      "board_net": "PIN60_IOR12A_MCS",
      "io_standard": "LVCMOS33",
      "frequency_hz": null,
      "active_polarity": null,
      "status": "verified"
    },
    {
      "interface": "spi_flash",
      "signal": "flash_mosi",
      "direction": "output",
      "package_pin": "61",
      "board_net": "PIN61_IOR11B_MOSI",
      "io_standard": "LVCMOS33",
      "frequency_hz": null,
      "active_polarity": null,
      "status": "verified"
    },
    {
      "interface": "spi_flash",
      "signal": "flash_miso",
      "direction": "input",
      "package_pin": "62",
      "board_net": "PIN62_IOR11A_MISO",
      "io_standard": "LVCMOS33",
      "frequency_hz": null,
      "active_polarity": null,
      "status": "verified"
    },
    {
      "interface": "sd_card",
      "signal": "sd_clk",
      "direction": "output",
      "package_pin": "36",
      "board_net": "PIN36_IOB29B_TF_SCLK",
      "io_standard": "LVCMOS33",
      "frequency_hz": null,
      "active_polarity": null,
      "status": "verified"
    },
    {
      "interface": "sd_card",
      "signal": "sd_cmd",
      "direction": "output",
      "package_pin": "37",
      "board_net": "PIN37_IOB31A_TF_MOSI",
      "io_standard": "LVCMOS33",
      "frequency_hz": null,
      "active_polarity": null,
      "status": "verified"
    },
    {
      "interface": "sd_card",
      "signal": "sd_dat0",
      "direction": "input",
      "package_pin": "39",
      "board_net": "PIN39_IOB33A_TF_MISO",
      "io_standard": "LVCMOS33",
      "frequency_hz": null,
      "active_polarity": null,
      "status": "verified"
    },
    {
      "interface": "sd_card",
      "signal": "sd_dat3_cs",
      "direction": "output",
      "package_pin": "38",
      "board_net": "PIN38_IOB31B_TF_CS",
      "io_standard": "LVCMOS33",
      "frequency_hz": null,
      "active_polarity": null,
      "status": "verified"
    },
    {
      "interface": "spi_lcd",
      "signal": "lcd_data",
      "direction": "output",
      "package_pin": "77",
      "board_net": "PIN77_IOT37A_SPILCD_MO",
      "io_standard": "LVCMOS33",
      "frequency_hz": null,
      "active_polarity": null,
      "status": "verified"
    },
    {
      "interface": "spi_lcd",
      "signal": "lcd_rs",
      "direction": "output",
      "package_pin": "49",
      "board_net": "PIN49_IOR24A_SPILCD_RS",
      "io_standard": "LVCMOS33",
      "frequency_hz": null,
      "active_polarity": null,
      "status": "verified"
    },
    {
      "interface": "spi_lcd",
      "signal": "lcd_cs",
      "direction": "output",
      "package_pin": "48",
      "board_net": "PIN48_IOR24B_SPILCD_CS",
      "io_standard": "LVCMOS33",
      "frequency_hz": null,
      "active_polarity": null,
      "status": "verified"
    },
    {
      "interface": "spi_lcd",
      "signal": "lcd_clk",
      "direction": "output",
      "package_pin": "76",
      "board_net": "PIN76_IOT37B_SPILCD_MCLK",
      "io_standard": "LVCMOS33",
      "frequency_hz": null,
      "active_polarity": null,
      "status": "verified"
    },
    {
      "interface": "spi_lcd",
      "signal": "lcd_resetn",
      "direction": "output",
      "package_pin": "47",
      "board_net": "PIN47_IOB43B_SPILCD_EN",
      "io_standard": "LVCMOS33",
      "frequency_hz": null,
      "active_polarity": null,
      "status": "verified"
    }
  ],
  "interfaces": [
    {
      "id": "clock",
      "name": "Default system clock",
      "status": "verified_in_constraints",
      "signals": [
        {
          "name": "clk",
          "direction": "input",
          "mapping_status": "verified",
          "package_pin": "52",
          "example_aliases": [
            "sys_clk"
          ]
        }
      ],
      "unresolved": [],
      "metadata": {}
    },
    {
      "id": "leds",
      "name": "User LEDs",
      "status": "verified_in_constraints",
      "signals": [
        {
          "name": "led[0]",
          "direction": "output",
          "mapping_status": "verified",
          "package_pin": "10",
          "active_polarity": "active_low",
          "example_aliases": [
            "gpio[0]"
          ]
        },
        {
          "name": "led[1]",
          "direction": "output",
          "mapping_status": "verified",
          "package_pin": "11",
          "active_polarity": "active_low",
          "example_aliases": [
            "gpio[1]"
          ]
        },
        {
          "name": "led[2]",
          "direction": "output",
          "mapping_status": "verified",
          "package_pin": "13",
          "active_polarity": "active_low",
          "example_aliases": [
            "gpio[2]"
          ]
        },
        {
          "name": "led[3]",
          "direction": "output",
          "mapping_status": "verified",
          "package_pin": "14",
          "active_polarity": "active_low",
          "example_aliases": [
            "gpio[3]"
          ]
        },
        {
          "name": "led[4]",
          "direction": "output",
          "mapping_status": "verified",
          "package_pin": "15",
          "active_polarity": "active_low",
          "example_aliases": [
            "gpio[4]"
          ]
        },
        {
          "name": "led[5]",
          "direction": "output",
          "mapping_status": "verified",
          "package_pin": "16",
          "active_polarity": "active_low",
          "example_aliases": [
            "gpio[5]"
          ]
        }
      ],
      "unresolved": [],
      "metadata": {}
    },
    {
      "id": "buttons",
      "name": "User buttons / reset inputs",
      "status": "verified_in_constraints",
      "signals": [
        {
          "name": "button_s1",
          "direction": "input",
          "mapping_status": "verified",
          "package_pin": "3",
          "active_polarity": "active_low",
          "example_aliases": [
            "rst_n",
            "gpio[6]"
          ]
        },
        {
          "name": "button_s2",
          "direction": "input",
          "mapping_status": "verified_with_caution",
          "package_pin": "4",
          "active_polarity": "active_low",
          "example_aliases": [
            "resetn",
            "sys_rst_n"
          ]
        }
      ],
      "unresolved": [],
      "metadata": {}
    },
    {
      "id": "uart",
      "name": "UART",
      "status": "verified_in_constraints",
      "signals": [
        {
          "name": "uart_tx",
          "direction": "output",
          "mapping_status": "verified",
          "package_pin": "17",
          "example_aliases": [
            "ser_tx"
          ]
        },
        {
          "name": "uart_rx",
          "direction": "input",
          "mapping_status": "verified",
          "package_pin": "18",
          "example_aliases": [
            "ser_rx"
          ]
        }
      ],
      "unresolved": [],
      "metadata": {}
    },
    {
      "id": "hdmi",
      "name": "HDMI TMDS",
      "status": "verified_in_constraints",
      "signals": [
        {
          "name": "tmds_clk_p",
          "direction": "output",
          "mapping_status": "verified",
          "package_pins": [
            "69",
            "68"
          ],
          "constraint_signal": "hdmi_clk_p"
        },
        {
          "name": "tmds_d_p[0]",
          "direction": "output",
          "mapping_status": "verified",
          "package_pins": [
            "71",
            "70"
          ],
          "constraint_signal": "hdmi_d0_p"
        },
        {
          "name": "tmds_d_p[1]",
          "direction": "output",
          "mapping_status": "verified",
          "package_pins": [
            "73",
            "72"
          ],
          "constraint_signal": "hdmi_d1_p"
        },
        {
          "name": "tmds_d_p[2]",
          "direction": "output",
          "mapping_status": "verified",
          "package_pins": [
            "75",
            "74"
          ],
          "constraint_signal": "hdmi_d2_p"
        }
      ],
      "unresolved": [
        "HDMI SDA",
        "HDMI SCL",
        "HDMI HPD",
        "HDMI CEC"
      ],
      "metadata": {}
    },
    {
      "id": "spi_flash",
      "name": "SPI flash",
      "status": "verified_in_constraints",
      "signals": [
        {
          "name": "flash_cs",
          "direction": "output",
          "mapping_status": "verified",
          "package_pin": "60",
          "example_aliases": [
            "flash_csb"
          ]
        },
        {
          "name": "flash_sck",
          "direction": "output",
          "mapping_status": "verified",
          "package_pin": "59",
          "example_aliases": [
            "flash_clk"
          ]
        },
        {
          "name": "flash_mosi",
          "direction": "inout",
          "mapping_status": "verified",
          "package_pin": "61"
        },
        {
          "name": "flash_miso",
          "direction": "inout",
          "mapping_status": "verified",
          "package_pin": "62"
        }
      ],
      "unresolved": [],
      "metadata": {
        "flash_part": "PUYA P25Q32U",
        "flash_capacity": "32 Mbit",
        "supported_mode": "DSPI",
        "sources": [
          "C:\\Documents\\Project_docs\\TANG\\TANG\\Nano 9K\\2_Schematic\\Tang_Nano_9k_3672_Schematic.pdf:U3",
          "accepted flash metadata update"
        ]
      }
    },
    {
      "id": "sd_card",
      "name": "SD card / TF card SPI mode",
      "status": "verified_in_constraints",
      "signals": [
        {
          "name": "sd_clk",
          "direction": "output",
          "mapping_status": "verified",
          "package_pin": "36"
        },
        {
          "name": "sd_cmd",
          "direction": "output",
          "mapping_status": "verified",
          "package_pin": "37",
          "spi_alias": "sd_mosi"
        },
        {
          "name": "sd_dat0",
          "direction": "input",
          "mapping_status": "verified",
          "package_pin": "39",
          "spi_alias": "sd_miso"
        },
        {
          "name": "sd_dat3_cs",
          "direction": "output",
          "mapping_status": "verified",
          "package_pin": "38",
          "spi_alias": "sd_cs"
        }
      ],
      "unresolved": [
        "SD DAT1",
        "SD DAT2",
        "SD card detect"
      ],
      "metadata": {}
    },
    {
      "id": "spi_lcd",
      "name": "1.14 inch SPI LCD header",
      "status": "verified_in_constraints",
      "signals": [
        {
          "name": "lcd_data",
          "direction": "output",
          "mapping_status": "verified",
          "package_pin": "77"
        },
        {
          "name": "lcd_rs",
          "direction": "output",
          "mapping_status": "verified",
          "package_pin": "49"
        },
        {
          "name": "lcd_cs",
          "direction": "output",
          "mapping_status": "verified",
          "package_pin": "48"
        },
        {
          "name": "lcd_clk",
          "direction": "output",
          "mapping_status": "verified",
          "package_pin": "76"
        },
        {
          "name": "lcd_resetn",
          "direction": "output",
          "mapping_status": "verified",
          "package_pin": "47"
        }
      ],
      "unresolved": [],
      "metadata": {}
    }
  ],
  "validation": {
    "status": "pass_v1.0_complete",
    "summary": {
      "total_signals": 39,
      "verified_signals": 32,
      "unverified_signals": 7,
      "constraint_signals": 32,
      "interfaces_declared": 8,
      "interfaces_with_constraints": 8,
      "missing_references_count": 0,
      "duplicate_mappings_count": 0,
      "schema_violations_count": 0
    },
    "readiness_score": {
      "hdl_generation": {
        "score": 96,
        "status": "ready",
        "basis": "All core HDL-facing signals are verified; unresolved items are optional HDMI auxiliary and non-SPI SD signals that should not be generated by default."
      },
      "constraint_generation": {
        "score": 99,
        "status": "ready",
        "basis": "All 32 emitted physical constraints resolve against pins.json with no duplicate logical or package-pin mappings."
      },
      "board_programming": {
        "score": 98,
        "status": "ready",
        "basis": "Clock, reset/button, UART, flash pins, and verified flash part metadata are available for programming workflows."
      },
      "interface_utilization": {
        "score": 91,
        "status": "ready_for_verified_interfaces",
        "basis": "Clock, LEDs, buttons, UART, HDMI TMDS, SPI flash, SD SPI mode, and SPI LCD are usable; auxiliary HDMI and full SD/card-detect remain gated."
      }
    },
    "remaining_unresolved_signals": [
      {
        "interface_id": "hdmi",
        "signal_name": "hdmi_sda",
        "reason": "HDMI SDA connector-side label appears in local schematic text, but no verified FPGA/package-pin mapping is available.",
        "mapping_status": "unverified",
        "status": "unverified"
      },
      {
        "interface_id": "hdmi",
        "signal_name": "hdmi_scl",
        "reason": "HDMI SCL connector-side label appears in local schematic text, but no verified FPGA/package-pin mapping is available.",
        "mapping_status": "unverified",
        "status": "unverified"
      },
      {
        "interface_id": "hdmi",
        "signal_name": "hdmi_hpd",
        "reason": "HDMI HPD connector-side label appears in local schematic text, but no verified FPGA/package-pin mapping is available.",
        "mapping_status": "unverified",
        "status": "unverified"
      },
      {
        "interface_id": "hdmi",
        "signal_name": "hdmi_cec",
        "reason": "HDMI CEC/HCEC connector-side label appears in local schematic text, but no verified FPGA/package-pin mapping is available.",
        "mapping_status": "unverified",
        "status": "unverified"
      },
      {
        "interface_id": "sd_card",
        "signal_name": "sd_dat1",
        "reason": "TF card DAT1 connector-side label appears in local schematic text, but no verified FPGA/package-pin mapping is available.",
        "mapping_status": "unverified",
        "status": "unverified"
      },
      {
        "interface_id": "sd_card",
        "signal_name": "sd_dat2",
        "reason": "TF card DAT2 connector-side label appears in local schematic text, but no verified FPGA/package-pin mapping is available.",
        "mapping_status": "unverified",
        "status": "unverified"
      },
      {
        "interface_id": "sd_card",
        "signal_name": "sd_card_detect",
        "reason": "No verified FPGA/package-pin mapping for SD card detect is available in the local sources checked.",
        "mapping_status": "unverified",
        "status": "unverified"
      }
    ],
    "reference_board_gate": {
      "passes_validation": true,
      "ready_as_reference_package": true,
      "board_package_status": "v1.0_complete",
      "blocking_issues": [],
      "remaining_gaps": [
        "HDMI SDA",
        "HDMI SCL",
        "HDMI HPD",
        "HDMI CEC",
        "SD DAT1",
        "SD DAT2",
        "SD card detect"
      ],
      "next_recommended_actions": [
        "Do not generate HDL or constraints for unresolved auxiliary signals until verified FPGA/package-pin mappings are available.",
        "Use the Tang Nano 9K package as the reference board package for onboarding the next supported board."
      ]
    }
  }
}

User request:
Generate a Verilog file 'led_blinker.v' and a Gowin .cst file 'led_blinker.cst'. The clock is 27MHz on pin 52. The LED is active-low on pin 10. The blink rate should be 1Hz (toggles every 13.5 million cycles).

Return the answer in this structure:
1. Short implementation note
2. HDL code, if applicable
3. Constraint snippets, if applicable
4. Verification or next command, if applicable

