import { world, system, ItemStack, Player } from "@minecraft/server";

const blockMap = new Map();
const chargedCreepers = new Map();
const halloween = new Date("October 31");

const headArray = [
    //[item identifier, block identifier, block tag, sound]
    ["cph:player_head", "cph:player_head_block", "player_head", "head.default"],
    ["cph:herobrine_head", "cph:herobrine_head_block", "herobrine_head", "head.cave1"]
];

function runCommand(command) {
    system.run(() => {
        world.getDimension("overworld").runCommand(command);
    });
}

/* 
    Players Drop Heads
*/

world.beforeEvents.entityRemove.subscribe((event) => {
    const removedEntity = event.removedEntity;

    if (removedEntity.typeId == "minecraft:creeper" && removedEntity.getComponent('is_charged')) 
    {
        chargedCreepers.set(removedEntity.id, true)
    }
});

world.afterEvents.entityDie.subscribe((event) => {
    const {damageSource, deadEntity} = event;
    const damagingEntity = damageSource.damagingEntity;

    if (deadEntity instanceof Player && (damagingEntity instanceof Player || chargedCreepers.has(damagingEntity.id)))
    {
        const deadPlayerNameSplit = deadEntity.name.toLowerCase().split(" ");
        const deadPlayerName = deadPlayerNameSplit.join("_");

        try {
            const month = new Date().getMonth();
            const day = new Date().getDate();
            let head;

            //halloween head

            if (month == halloween.getMonth() && day == halloween.getDate())
            {
                head = new ItemStack(`cph:herobrine_head_block`) 
            }
            else
            {
                head = new ItemStack(`cph:${deadPlayerName}_head_block`)  
            }

            if (!chargedCreepers.has(damagingEntity.id))
            {
                const killerPlayerName = damagingEntity.nameTag?damagingEntity.nameTag:damagingEntity.typeId.split(":")[1]
                head.setLore([`Killed by ${killerPlayerName}`])
            }
            else 
            {
                chargedCreepers.delete(damagingEntity.id);
            }

            deadEntity.dimension.spawnItem(head, deadEntity.location);
            
        } catch (error) {
            console.warn(`There was an error spawning ${deadPlayerName}\'s head`);
        }
    }
});

/* 
    Block Rotation
*/

/** @param {number} playerYRotation */
function getPreciseRotation(playerYRotation) {
    if (playerYRotation < 0) playerYRotation += 360;
    const rotation = Math.round(playerYRotation / 22.5);

    return rotation !== 16 ? rotation : 0;
};

/** @type {import("@minecraft/server").BlockCustomComponent} */
const RotationBlockComponent = {
    beforeOnPlayerPlace(event) {
        const { player } = event;
        if (!player) return;

        const blockFace = event.permutationToPlace.getState("minecraft:block_face");
        if (blockFace !== "up") return;

        const playerYRotation = player.getRotation().y;
        const rotation = getPreciseRotation(playerYRotation);

        event.permutationToPlace = event.permutationToPlace.withState("cph:head_rotation", rotation);
    }
};

world.beforeEvents.worldInitialize.subscribe(({ blockComponentRegistry }) => {
    blockComponentRegistry.registerCustomComponent("cph:rotation_comp", RotationBlockComponent);
});

/* 
    Noteblock Functionality
*/

//redstone power
world.beforeEvents.worldInitialize.subscribe(eventData =>{eventData.blockComponentRegistry.registerCustomComponent('cph:check_noteblock', {
    onTick(event) { 
    const block = event.block;
    const blockBelow = block.below();
    const currentRedstonePower = blockBelow.getRedstonePower();
    const { x, y, z } = blockBelow.location
    const blockKey = `${x}*${y}*${z}`
    const blockObject = blockMap.get(blockKey) ?? {};
    const { previousRedstonePower } = blockObject;

    if (blockBelow.typeId == "minecraft:noteblock" && currentRedstonePower > 0 && currentRedstonePower != previousRedstonePower) {
        const location = blockBelow.location;
        for (let i = 0; i < headArray.length; i++) {
            if (block.typeId == headArray[i][1]) {
                world.playSound(headArray[i][3], location)
                break;
            }
        }
    }
    blockObject.previousRedstonePower = currentRedstonePower;
    blockMap.set(blockKey, blockObject)
}
})});

//Noteblock interaction
world.afterEvents.playerInteractWithBlock.subscribe((event) => {
    const { player } = event;
    if (!player) return;
    const block = event.block;
    const blockAbove = block.dimension.getBlock({ x: block.location.x, y: (block.location.y) + 1, z: block.location.z });

    if(!(player.isSneaking && event.beforeItemStack != null))
    {
      if (block.typeId == "minecraft:noteblock") {
          for (let i = 0; i < headArray.length; i++) {
              if (blockAbove.typeId == headArray[i][1]) {
                world.playSound(headArray[i][3], block.location) 
                break;
              }
          }
      }
    }
});

//Stop sound when noteblock or head is destroyed
world.beforeEvents.playerBreakBlock.subscribe((event) => {
    const block = event.block;

    if (block.typeId == "minecraft:noteblock") {
        const blockAbove = block.dimension.getBlock({ x: block.location.x, y: (block.location.y) + 1, z: block.location.z });
        if (!blockAbove.typeId.startsWith("cph")) return;

        for (let i = 0; i < headArray.length; i++) {
            if (blockAbove.typeId == headArray[i][1]) {
                const command = `stopsound @a ${headArray[i][3]}`;
                runCommand(command);
                break;
            }
        }
    }
    else if (block.typeId.startsWith("cph")) {
        const blockBelow = block.dimension.getBlock({ x: block.location.x, y: (block.location.y) - 1, z: block.location.z });
        if (!blockBelow.typeId == "minecraft:noteblock") return;

        for (let i = 0; i < headArray.length; i++) {
            if (block.typeId == headArray[i][1]) {
                const command = `stopsound @a ${headArray[i][3]}`;
                runCommand(command);
                break;
            }
        }
    }
});

//Stop sound when changing dimensions
world.afterEvents.playerDimensionChange.subscribe((event) => {
    const { player } = event;
    if (!player) return;

    for (let i = 0; i < headArray.length; i++) {
        const command = `stopsound ${player.name} ${headArray[i][3]}`;
        runCommand(command);
    }
});