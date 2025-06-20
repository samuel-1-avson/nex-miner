# Nex Miner

<p align="center">
  <img src="https://raw.githubusercontent.com/username/repo/main/gameplay.gif" alt="Nex Miner Gameplay GIF" width="640"/>
  <br/>
  <i>An AI-Enhanced Vertical Roguelike Platformer.</i>
</p>

---

### About The Game

**Nex Miner** is a fast-paced, vertical-scrolling roguelike created for the **Nexus Playground Contest**. As an "Operative," you must delve into an infinite, procedurally generated data-tower, climbing an ever-stacking pile of falling data-blocks while battling digital hazards and rogue AI constructs.

The core of Nex Miner is its deep integration with a generative AI. Talk to the **Mainframe** to generate your own *completely unique, playable characters*, receive dynamic mission directives, or simply ask for guidance. Every run is different, with a vast pool of perks, artifacts, curses, and biomes to discover.

### Key Features

-   **Infinite Roguelike Gameplay:** No two runs are the same. Climb as high as you can through procedurally generated biomes.
-   **AI-Powered Character Generation:** State your "core directive" to the Mainframe and have it generate a new Operative with unique perks and starting items, tailored to your input.
-   **Deep Progression:** Collect nanocoins to unlock permanent upgrades, characters, and powerful artifacts that fundamentally change how you play.
-   **Dynamic Systems:** Combine dozens of in-run perks, survive dangerous curses, and utilize a wide array of items to create powerful synergies.
-   **Multiple Game Modes:** Choose between Standard, Zen, Hardcore, a Daily Seeded Challenge, or unique pre-built Simulation levels.

### Getting Started

To run Nex Miner locally, you will need Python 3 and an optional Google Gemini API Key.

1.  **Clone the repository:**
    ```sh
    git clone https://github.com/YOUR_USERNAME/nex-miner.git
    cd nex-miner
    ```

2.  **Install dependencies:**
    A `requirements.txt` file is included for easy installation.
    ```sh
    pip install -r requirements.txt
    ```

3.  **Set up your API Key (Optional):**
    The core game is fully playable without an AI. If you want to enable the Mainframe features:
    -   Create a file named `.env` in the root directory.
    -   Add your Google Gemini API Key to it like so:
        ```
        GEMINI_API_KEY="AIzaSy...your_key_here"
        ```

4.  **Run the game!**
    From the root directory of the repository, execute the following command:
    ```sh
    python "Nex Miner/Nex Miner/Nex Miner/Nex miner/Nex Miner/Nex Miner.py"
    ```

### Controls

| Key(s) | Action |
| :--- | :--- |
| **A / D or ← / →** | Move Left / Right |
| **W / ↑ or Space** | Jump |
| **C or L (Release)** | Dash |
| **Left Shift (Hold)**| Chrono-Shift (Slow Time) |
| **Z or K** | Fire Projectile |
| **E or X** | Use Equipped Item |
| **Enter** | Confirm |
| **Escape** | Back / Pause |

### Acknowledgements

This project was heavily inspired by the brilliant work of **DaFluffyPotato**. The initial game architecture, physics, and core mechanics are a loving adaptation of his open-source game, **Cavyn**. His tutorials and code have been an invaluable learning resource.


### The Nexus Playground Contest

This game is an entry for the second Nexus Playground creative contest, designed to capture the values, culture, and aesthetic of Nexus. It is fully open-source, shareable, and built with interactivity and community at its core.

### License

This project is licensed under the MIT License. See the `LICENSE` file for details.
