import { world, system, ItemStack, Player } from "@minecraft/server";

const blockMap = new Map();
const chargedCreepers = new Map();
const halloween = new Date("October 31");

const headArray = [];

function runCommand(command, dimension) {
    system.run(() => {
        dimension.runCommand(command);
    });
}

/* 
    Players Drop Heads
*/

world.beforeEvents.entityRemove.subscribe(({ removedEntity }) => {
    if (removedEntity.typeId == "minecraft:creeper" && removedEntity.getComponent("minecraft:is_charged")) {
        chargedCreepers.set(removedEntity.id, true);
    }
})

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

function getPreciseRotation(playerYRotation) {
    if (playerYRotation < 0) playerYRotation += 360;
    const rotation = Math.round(playerYRotation / 22.5);

    return rotation !== 16 ? rotation : 0;
};

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

system.beforeEvents.startup.subscribe((initEvent) => {
    initEvent.blockComponentRegistry.registerCustomComponent("cph:rotation_comp", RotationBlockComponent);
});


/* 
    Noteblock Functionality
*/

// Redstone power
system.beforeEvents.startup.subscribe(eventData => {
    eventData.blockComponentRegistry.registerCustomComponent('cph:check_noteblock', {
        onTick(event) {
            const block = event.block;
            const neighbors = [
                block.north(),
                block.south(),
                block.east(),
                block.west(),
                block.below(),
            ];

            for (const neighbor of neighbors) {
                if (!neighbor || neighbor.typeId !== "minecraft:noteblock") continue;

                const { x, y, z } = neighbor.location;
                const blockKey = `${x}*${y}*${z}`;
                const blockObject = blockMap.get(blockKey) ?? {};
                const { previousPowered } = blockObject;

                const powerNeighbors = [
                    neighbor.north(),
                    neighbor.south(),
                    neighbor.east(),
                    neighbor.west(),
                    neighbor.below(),
                ];
                const currentPowered = powerNeighbors.some(n => (n?.getRedstonePower() ?? 0) > 0);

                if (currentPowered && !previousPowered) {
                    for (let i = 0; i < headArray.length; i++) {
                        if (block.typeId == headArray[i][1]) {
                            neighbor.dimension.playSound(headArray[i][3], neighbor.location, { volume: 100.0 });
                            break;
                        }
                    }
                }

                blockObject.previousPowered = currentPowered;
                blockMap.set(blockKey, blockObject);
            }
        }
    })
});

// Noteblock interaction
world.afterEvents.playerInteractWithBlock.subscribe((eventData) => {
    const { player } = eventData;
    if (!player) return;

    const item = player.getComponent('minecraft:equippable')?.getEquipment('Mainhand');

    if (!(player.isSneaking)) {
        const block = eventData.block;
        const dimension = block.dimension;
        const blockAbove = block.dimension.getBlock({ x: block.location.x, y: (block.location.y) + 1, z: block.location.z });
        if (block.typeId == "minecraft:noteblock") {
            for (let i = 0; i < headArray.length; i++) {
                if (blockAbove.typeId == headArray[i][1]) {
                    dimension.playSound(headArray[i][3], block.location, { volume: 100.0 });
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
                runCommand(command, block.dimension);
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
                runCommand(command, block.dimension);
                break;
            }
        }
    }
});