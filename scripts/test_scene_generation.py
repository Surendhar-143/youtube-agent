import os
import sys
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up logging to console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

from agents.scene_agent import SceneAgent

def main():
    agent = SceneAgent()
    # Try to generate scenes for script ID 2
    try:
        scenes = agent.generate_scenes(2)
        print(f"Successfully generated {len(scenes)} scenes!")
    except Exception as e:
        print(f"Scene generation failed: {e}")

if __name__ == "__main__":
    main()
