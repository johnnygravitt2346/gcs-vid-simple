#!/usr/bin/env python3
"""
Convert Gemini-generated CSV to video generator format
"""

import csv

# Read the Gemini-generated CSV
with open('gemini_generated_dataset.csv', 'r') as f:
    reader = csv.DictReader(f)
    
    # Create video generator format CSV
    with open('test_trivia.csv', 'w', newline='') as out_f:
        writer = csv.writer(out_f)
        
        # Write header
        writer.writerow(['Question', 'OptionA', 'OptionB', 'OptionC', 'OptionD', 'Correct Answer'])
        
        # Convert each row
        for row in reader:
            # Map Gemini format to video generator format
            question = row['question']
            option_a = row['option_a']
            option_b = row['option_b']
            option_c = row['option_c']
            option_d = row['option_d']
            
            # Convert answer key (A, B, C, D) to actual answer text
            answer_map = {'A': option_a, 'B': option_b, 'C': option_c, 'D': option_d}
            correct_answer = answer_map.get(row['answer_key'], option_a)
            
            writer.writerow([question, option_a, option_b, option_c, option_d, correct_answer])

print("✅ Converted Gemini CSV to video generator format: test_trivia.csv")
print("📊 Generated 3 trivia questions for video rendering")
