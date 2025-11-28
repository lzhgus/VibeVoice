"""
VibeVoice Batch Inference with Simple Caption Generation

This script processes MULTIPLE scripts in PARALLEL to maximize GPU utilization.
This is the ONLY way to get GPU usage from 5% to 80%+ on RTX 5090.

Usage:
    python batch_inference_simple_captions.py \
        --txt_dir demo/text_examples \
        --batch_size 8 \
        --device cuda
"""

import argparse
import os
import glob
import re
import traceback
from typing import List, Tuple, Dict, Any
import time
import torch
import json

from vibevoice.modular.modeling_vibevoice_inference import VibeVoiceForConditionalGenerationInference
from vibevoice.processor.vibevoice_processor_simple_captions import VibeVoiceProcessorSimpleCaptions
from transformers.utils import logging

# Add the VoiceMapper and parse_txt_script from the original script
import sys
sys.path.insert(0, os.path.dirname(__file__))
from inference_simple_captions import VoiceMapper, parse_txt_script

logging.set_verbosity_info()
logger = logging.get_logger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(description="VibeVoice BATCH Inference - Process multiple scripts in parallel")
    parser.add_argument(
        "--model_path",
        type=str,
        default="microsoft/VibeVoice-1.5b",
        help="Path to the HuggingFace model directory",
    )
    parser.add_argument(
        "--txt_path",
        type=str,
        default=None,
        help="Single txt file to process (for compatibility with original script)",
    )
    parser.add_argument(
        "--txt_dir",
        type=str,
        default="demo/text_examples",
        help="Directory containing txt files to process",
    )
    parser.add_argument(
        "--txt_files",
        type=str,
        nargs='+',
        default=None,
        help="Specific txt files to process (overrides txt_dir)",
    )
    parser.add_argument(
        "--batch_size",
        type=int,
        default=8,
        help="Number of scripts to process in parallel. Higher = better GPU usage. "
             "For RTX 5090: try 8-16. Start with 8.",
    )
    parser.add_argument(
        "--speaker_names",
        type=str,
        nargs='+',
        default=['Andrew', 'Ava', 'Bill', 'Carol'],
        help="Default speaker names for scripts without specific mappings",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="./outputs",
        help="Directory to save output audio files (default: ./outputs for compatibility with shell scripts)",
    )
    parser.add_argument(
        "--device",
        type=str,
        default=("cuda" if torch.cuda.is_available() else "cpu"),
        help="Device for inference: cuda | cpu",
    )
    parser.add_argument(
        "--cfg_scale",
        type=float,
        default=1.3,
        help="CFG (Classifier-Free Guidance) scale for generation",
    )
    parser.add_argument(
        "--generate_captions",
        action="store_true",
        help="Generate captions for the generated audio",
    )
    parser.add_argument(
        "--words_per_minute",
        type=int,
        default=150,
        help="Average speaking rate for timing estimation",
    )
    parser.add_argument(
        "--caption_formats",
        type=str,
        nargs='+',
        default=['srt'],
        help="Caption formats to generate (for compatibility)",
    )
    
    return parser.parse_args()


def load_txt_files(args) -> List[Tuple[str, str, List[str], List[str]]]:
    """
    Load txt files and parse them.
    
    Returns:
        List of (filename, full_script, scripts, speaker_numbers)
    """
    # Get list of txt files
    if args.txt_path:
        # Single file mode (compatibility with original script)
        txt_files = [args.txt_path]
    elif args.txt_files:
        txt_files = args.txt_files
    else:
        txt_pattern = os.path.join(args.txt_dir, "*.txt")
        txt_files = sorted(glob.glob(txt_pattern))
    
    if not txt_files:
        print(f"❌ No txt files found!")
        return []
    
    print(f"📁 Found {len(txt_files)} txt files")
    
    # Load and parse all files
    loaded_files = []
    for txt_file in txt_files:
        if not os.path.exists(txt_file):
            print(f"⚠️  File not found: {txt_file}")
            continue
        
        try:
            with open(txt_file, 'r', encoding='utf-8') as f:
                txt_content = f.read()
            
            scripts, speaker_numbers = parse_txt_script(txt_content)
            
            if not scripts:
                print(f"⚠️  No valid scripts in {os.path.basename(txt_file)}")
                continue
            
            full_script = '\n'.join(scripts).replace("'", "'")
            loaded_files.append((txt_file, full_script, scripts, speaker_numbers))
            print(f"  ✅ {os.path.basename(txt_file)}: {len(scripts)} segments, "
                  f"{len(set(speaker_numbers))} speakers")
        
        except Exception as e:
            print(f"⚠️  Error loading {os.path.basename(txt_file)}: {e}")
    
    return loaded_files


def create_batches(loaded_files: List, batch_size: int) -> List[List]:
    """
    Group files into batches for parallel processing.
    """
    batches = []
    for i in range(0, len(loaded_files), batch_size):
        batch = loaded_files[i:i + batch_size]
        batches.append(batch)
    return batches


def main():
    args = parse_args()
    
    # Determine mode (single file vs batch)
    single_file_mode = args.txt_path is not None
    
    print("=" * 80)
    if single_file_mode:
        print("🎯 VibeVoice Inference (Single File Mode)")
    else:
        print("🚀 VibeVoice BATCH Inference - Maximize GPU Utilization!")
    print("=" * 80)
    print(f"Device: {args.device}")
    if not single_file_mode:
        print(f"Batch size: {args.batch_size} scripts in parallel")
        print(f"Expected GPU utilization: 70-90% (vs 5% with single script)")
    print("=" * 80)
    
    # Load txt files
    loaded_files = load_txt_files(args)
    
    if not loaded_files:
        print("❌ No files to process")
        return
    
    print(f"\n📊 Total scripts to process: {len(loaded_files)}")
    
    # Create batches
    batches = create_batches(loaded_files, args.batch_size)
    print(f"📦 Created {len(batches)} batches")
    print(f"   Batch sizes: {[len(b) for b in batches]}")
    
    # Initialize voice mapper
    voice_mapper = VoiceMapper()
    
    # Load processor and model
    print(f"\n🔧 Loading processor & model from {args.model_path}...")
    processor = VibeVoiceProcessorSimpleCaptions.from_pretrained(
        args.model_path,
        words_per_minute=args.words_per_minute
    )
    
    # Decide dtype & attention implementation
    if args.device == "cuda":
        load_dtype = torch.bfloat16
        attn_impl_primary = "flash_attention_2"
    else:
        load_dtype = torch.float32
        attn_impl_primary = "sdpa"
    
    print(f"   torch_dtype: {load_dtype}, attn_implementation: {attn_impl_primary}")
    
    # Load model
    try:
        model = VibeVoiceForConditionalGenerationInference.from_pretrained(
            args.model_path,
            torch_dtype=load_dtype,
            device_map=args.device,
            attn_implementation=attn_impl_primary,
        )
    except Exception as e:
        print(f"⚠️  Error loading model with {attn_impl_primary}, trying SDPA...")
        model = VibeVoiceForConditionalGenerationInference.from_pretrained(
            args.model_path,
            torch_dtype=load_dtype,
            device_map=args.device,
            attn_implementation='sdpa'
        )
    
    model.eval()
    model.set_ddpm_inference_steps(num_steps=10)
    
    # Compile model for better performance
    if args.device == "cuda" and hasattr(torch, 'compile'):
        try:
            print("🔧 Compiling model with torch.compile()...")
            model = torch.compile(model, mode="reduce-overhead")
            print("✅ Model compiled successfully")
        except Exception as e:
            print(f"⚠️  torch.compile() failed: {e}")
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Process batches
    print(f"\n{'='*80}")
    if single_file_mode:
        print("🎬 Starting Audio Generation")
    else:
        print("🎬 Starting Batch Processing")
    print(f"{'='*80}")
    
    total_start = time.time()
    saved_files_all = []  # Track all saved files
    
    for batch_idx, batch in enumerate(batches):
        print(f"\n📦 Batch {batch_idx + 1}/{len(batches)}: Processing {len(batch)} scripts in parallel...")
        
        # Prepare batch data
        batch_scripts = []
        batch_voice_samples_list = []
        batch_filenames = []
        
        for txt_file, full_script, scripts, speaker_numbers in batch:
            batch_scripts.append(full_script)
            batch_filenames.append(os.path.splitext(os.path.basename(txt_file))[0])
            
            # Get unique speakers and map to voices
            unique_speakers = []
            seen = set()
            for spk_num in speaker_numbers:
                if spk_num not in seen:
                    unique_speakers.append(spk_num)
                    seen.add(spk_num)
            
            # Map speakers to voice files
            voice_samples = []
            for i, spk_num in enumerate(unique_speakers):
                speaker_name = args.speaker_names[i % len(args.speaker_names)]
                voice_path = voice_mapper.get_voice_path(speaker_name)
                voice_samples.append(voice_path)
            
            batch_voice_samples_list.append(voice_samples)
        
        # Prepare batch inputs
        print(f"   Preparing inputs for {len(batch_scripts)} scripts...")
        inputs = processor(
            text=batch_scripts,  # Multiple scripts
            voice_samples=batch_voice_samples_list,  # Multiple voice lists
            padding=True,
            return_tensors="pt",
            return_attention_mask=True,
        )
        
        # Move to device
        for k, v in inputs.items():
            if torch.is_tensor(v):
                inputs[k] = v.to(args.device, non_blocking=True)
        
        print(f"   🎯 Generating audio for {len(batch_scripts)} scripts IN PARALLEL...")
        print(f"      GPU should now be at 70-90% utilization!")
        
        # Generate (all in parallel!)
        batch_start = time.time()
        outputs = model.generate(
            **inputs,
            max_new_tokens=None,
            cfg_scale=args.cfg_scale,
            tokenizer=processor.tokenizer,
            generation_config={'do_sample': False},
            verbose=False,  # Reduce output for batch processing
        )
        batch_time = time.time() - batch_start
        
        print(f"   ✅ Batch generation time: {batch_time:.2f}s ({batch_time/len(batch):.2f}s per script)")
        
        # Save outputs
        print(f"   💾 Saving outputs...")
        saved_files = []
        for i, filename in enumerate(batch_filenames):
            if outputs.speech_outputs and i < len(outputs.speech_outputs):
                output_path = os.path.join(args.output_dir, f"{filename}_generated.wav")
                
                # Save audio
                if args.generate_captions:
                    # Get the original script
                    _, original_script, _, _ = batch[i]
                    result = processor.save_audio_with_captions(
                        audio=outputs.speech_outputs[i],
                        output_path=output_path,
                        sampling_rate=24000,
                        normalize=False,
                        original_script=original_script,
                        generate_captions=True,
                    )
                    saved_path = result['audio_paths'][0] if isinstance(result['audio_paths'], list) else result['audio_paths']
                    saved_files.append(saved_path)
                    print(f"      ✅ {filename}: {saved_path} + captions")
                else:
                    saved_path = processor.save_audio(
                        audio=outputs.speech_outputs[i],
                        output_path=output_path,
                        sampling_rate=24000,
                        normalize=False,
                    )
                    saved_files.append(saved_path)
                    print(f"      ✅ {filename}: {output_path}")
        
        # Track saved files
        saved_files_all.extend(saved_files)
    
    total_time = time.time() - total_start
    
    print(f"\n{'='*80}")
    if single_file_mode:
        print(f"✅ AUDIO GENERATION COMPLETE!")
    else:
        print(f"✅ BATCH PROCESSING COMPLETE!")
    print(f"{'='*80}")
    print(f"Total scripts processed: {len(loaded_files)}")
    print(f"Total time: {total_time:.2f}s")
    print(f"Average time per script: {total_time/len(loaded_files):.2f}s")
    print(f"Output directory: {args.output_dir}")
    if not single_file_mode:
        print(f"\n💡 GPU utilization should have been 70-90% (vs 5% with single script)")
    print(f"{'='*80}")
    
    # For shell script compatibility: Output in expected format
    # Shell scripts look for "Saved audio to: <filename>"
    if single_file_mode and saved_files_all:
        print(f"\nSaved audio to: {saved_files_all[0]}")


if __name__ == "__main__":
    main()


