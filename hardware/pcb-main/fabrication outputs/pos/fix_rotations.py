import pandas as pd
import re

def load_rotation_rules(filename):
    rules = {}
    rotations_df = pd.read_csv(filename)
    for _, row in rotations_df.iterrows():
        pattern = row['Footprint pattern']
        rotation = row['Rotation']
        rules[pattern] = rotation
    return rules

def get_rotation_adjustment(package, rules):
    for pattern, adjustment in rules.items():
        if re.match(pattern, package):
            return adjustment
    return 0  # No adjustment if no pattern matches

def adjust_rotation(row, rules):
    package = row['Package']
    original = float(row['Rotation'])
    
    # Get rotation adjustment from rules
    adjustment = get_rotation_adjustment(package, rules)
    
    # Apply adjustment
    if row['Layer'].strip().lower() == 'bottom':
        new_rotation = (-original + 180) % 360
    else:
        new_rotation = (original + adjustment) % 360
        
    return new_rotation

# Load rotation rules
rules = load_rotation_rules('default_rotations.csv')

# Read the CSV
df = pd.read_csv('motion-play-v3-all-pos.csv')

# Apply rotation adjustment
df['Rotation'] = df.apply(lambda row: adjust_rotation(row, rules), axis=1)

# Save the modified file
df.to_csv('motion-play-v3-all-pos_adjusted.csv', index=False)

