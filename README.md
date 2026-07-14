# Custom Player Heads
<img width="1280" height="720" alt="thumbnail" src="https://github.com/user-attachments/assets/8d4acfc5-c0d8-429e-b575-f9a2b898b680" />

## Do you wish you could add your player head to Minecraft Bedrock edition? 

Do you wish you could get custom player heads from other killing players like on Java edition? This addon allows you to create your own player heads! 

## IMPORTANT: Please Read all the way through before you start messing with this addon!

Due to the limitations of Bedrock edition, player heads need to be pre-compiled instead of created on the fly. This basically means that you need to create each head from scratch before they appear in game. <ins>Because if this, you'll need to build the addon on a (windows) computer before you can use it!</ins> This repository contains a python script that builds the pack for you. You'll need to have some experience in asset creation to use this addon.

I recommend using [blockbench](https://www.blockbench.net/) for modeling and [audacity](https://www.audacityteam.org/) to convert your sound files to ogg.

Video Showcase: https://www.youtube.com/watch?v=bTtCwAQcXFU

## Installation

### Building from Source
- Download the source and extract it. 
- Place your head assets (models, sounds, textures) in the user assets folder. I added template files in the user assets folder to help you get started creating your own heads. Feel free to remove them if you desire.
- Edit the HeadsToCreate.csv and add the heads you wish to create.
- <ins>Before you move on, there are a few guidlines you need to follow.</ins>
  - Make sure the name of the head block matches the player it belongs to, otherwise that player will not drop their head!
  - If there are any spaces in the player's name for example "man dude", make sure to replace each of them with an underscore in the head name.
  - Make sure that the texture file has the same name as the head block, otherwise you'll have to define it in the textures column.
  - The sound and model column should not be left empty.
  - If you'd like the item name to have a different display name you can chose to do so here!
    
    <img width="471" height="82" alt="Screenshot 2026-07-13 212839" src="https://github.com/user-attachments/assets/287f61fd-f335-4b9e-bf0b-e46b37ddd50a" />
- Then, run createHeads.py (you're gonna need python).

The script will then generate the RP and BP folders for you to import into Minecraft. Make sure to delete these two folders before running the script again!

## Acknowledgments

### Special Thanks

- **[Bedrock Addons Community](https://wiki.bedrock.dev/)** - For providing the documentation required to make this addon
- **[crstalli](https://github.com/crstalli)** - For updating the noteblock functionality in my absence
