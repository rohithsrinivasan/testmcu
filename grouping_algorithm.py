def group_port_pins(value): # Done only when Pin name starts with P
    def get_port_name(prefix, port_type, start_idx):
        if len(value) == start_idx + 2:
            if value[start_idx] in '0123456789':
                return f'{port_type} {value[start_idx]}'
            elif value[start_idx] in 'ABCDEFGH':
                return f'{port_type} {value[start_idx]}'
        
        elif len(value) in (start_idx + 3, start_idx + 4) and value[start_idx] in '0123456789ABCDEFGH' and value[start_idx + 1] == '_':
            return f'{port_type} {value[start_idx:start_idx + 1]}'
        
        elif len(value) == start_idx + 4 and value[start_idx:start_idx + 2] in '11121314151617181920' and value[start_idx + 2] == '_':
            return f'{port_type} {value[start_idx:start_idx + 2]}'
        
        elif value[start_idx:start_idx + 2] in '101112131415':
            return f'{port_type} {value[start_idx:start_idx + 2]}'
        
        return None

    if value.startswith('P'):
        return get_port_name('P', 'Port', 1)
    elif value.startswith('AP'):
        return get_port_name('AP', 'Port Analog', 2)
    elif value.startswith('JP'):
        return get_port_name('JP', 'Port JTAG', 2)

    return None


def group_other_io_pins(row):
    pin_groups = {
        "I2C_Pins": ['SDA', 'SCL', r'\SDA', r'\SCL', 'SDO', r'\SDO'],
        "GPIO_Pins": ['GPIO'],
        "Main_Clock": ['XOUT', 'XIN'],
        "ADC_Pins": ['ADC'],
        "Analog_Input_Pins": ['AIN',"Ain"]
    }

    if row['Electrical Type'] == 'I/O':
        for group, prefixes in pin_groups.items():
            if row['Pin Display Name'].startswith(tuple(prefixes)):
                return group

    return None
 
def group_output_pins(row):
    output_pin_groups = {
        'Common_Output': ['COM'],
        'System': ['RES'],
        'Main_Clock': ['XOUT'],
        'External_Clock_Capacitor': ['XCOUT', 'XT'],
        'On_Chip_Oscillator': ['TRST', '\TRST' ,'TMS', 'TDI', 'TCK', 'TDO']
    }

    if row['Electrical Type'] == 'Output':
        for group, prefixes in output_pin_groups.items():
            if row['Pin Display Name'].startswith(tuple(prefixes)):
                return group
        return 'System_Output'  # Default for unmatched Output types

    return None


def group_power_pins(row):
    pin_groups = {
        "Power_Positive": ['VDD','SMVDD', 'EVD', 'CVD', 'VCC','PLLVCC','A0VCC','A1VCC','A2VCC','RVCC','SYSVCC','EVCC','BVCC','CVCC','DVCC','ISOVCC','AWOVC'],
        "Power_Negetive": ['VSS','SMVSS', 'EVS', 'CVS', 'Epa', 'EPA', 'GND','PLLVSS','A0VSS','A1VSS','A2VSS','RVSS','AVSS','BVSS','CVSS','DVSS','ISOVSS','AWOVS','VCL','ISOVCL'],
        "Power_Negetive_Regulator_Capacitor": ['REG','AREGC'],
        "Power_Ref_Positive": ['REF', 'AVREF', 'A1VREF', 'A2VREF', 'VREF', 'A0VREF'],
        "Power_Ref_Negetive": ['REFL'],
        "Power_Low_Positive": ['VL','Vl'],
        "Power_High_Positive": ['VH','Vh'],
        "Power_Battery_Management": ["VRTC", "VBAT", "AVRT", "AVCM"],
        "Analog_Power_Positive": ['AVCC', 'AVDD'],
        "Analog_Power_Negetive": ['AVS', 'AWOVSS'],
        "Audio_data_lines": ['AUD','\AUD'],
        "Control": ['RDC', 'FLMD'],
        "Cutoff": ['DCUT', r'\DCUT'],
    }

    if row['Electrical Type'] == 'Power':
        pin_name = row['Pin Display Name']
        prefix = pin_name[:3]
        suffix = pin_name[3:7]
        
        # Check pin groups by prefix, suffix, or full pin name
        for group, prefixes in pin_groups.items():
            if any(pin_name.startswith(prefix) for prefix in prefixes) or pin_name in prefixes:
                return group
            
        # Fallback for unmatched power pins
        #return f'P{prefix[1]}_Other_Power_Pin'
        return None

    elif row['Electrical Type'] in ['Input', 'I/O']:
        # Check for groups that apply to Input or I/O pins
        for group, prefixes in pin_groups.items():
            if any(row['Pin Display Name'].startswith(prefix) for prefix in prefixes):
                return group

    return None

def group_input_pins(row):
    pin_groups = {
        "External_Clock": ["XT", "EX"],
        "System": ["\R", "\S", "FW", "RESET", "UB", "EMLE"],
        "Mode": ["MD", "MO", "MODE","FLMODE"],
        "Interrupt": ["NMI"],
        "P+ Analog": ["Vr"],
        "Power_Ref_Positive" : ["REF"],
        "Main_Clock": ["X1", "X2", "XI"],
        "External_Clock_Capacitor": ["XC"],
        "Chip_Select": ["CS", "nCS"],
        "ADC_Pins": ["ADC", "ADCC"],
        "Reference_Clk": ["CLKIN"],
        "Reset": ["nMR"],
        "On_Chip_Oscillator": ["TRST","\TRST", "TMS", "TDI", "TCK", "TDO", "OS"],
        "I_Analog_Input_Pins": ["ANIN", "ANIP"],
    }

    if row['Electrical Type'] == "Input":
        pin_name = row['Pin Display Name']
        
        # Check for matches in pin groups by prefix
        for group, prefixes in pin_groups.items():
            if any(pin_name.startswith(prefix) for prefix in prefixes):
                return group

    # Handling for pins that are both Input and Output types
    if row['Electrical Type'] in ("Input", "Output") and any(
        row['Pin Display Name'].startswith(prefix) for prefix in pin_groups["On_Chip_Oscillator"]
    ):
        return "On_Chip_Oscillator"

    return None


def group_passsive_pins(row):
   
    passive_prefixes = ['NC']
    if row['Electrical Type'] == 'Passive' and row['Pin Display Name'].startswith(tuple(passive_prefixes)):
        return f'No_Connect'