#ifndef MEMORY_MONITOR_H
#define MEMORY_MONITOR_H

#include <Arduino.h>
#include <esp_heap_caps.h>
#include <esp_system.h>

/**
 * Memory monitoring utility for detecting heap exhaustion and memory leaks
 * Tracks both internal RAM and PSRAM usage
 */
class MemoryMonitor
{
public:
    /**
     * Print detailed memory statistics to Serial
     */
    static void printMemoryStats()
    {
        Serial.println("\n=== MEMORY STATISTICS ===");

        // Internal RAM (heap)
        size_t freeHeap = heap_caps_get_free_size(MALLOC_CAP_8BIT);
        size_t totalHeap = heap_caps_get_total_size(MALLOC_CAP_8BIT);
        size_t usedHeap = totalHeap - freeHeap;
        size_t minFreeHeap = heap_caps_get_minimum_free_size(MALLOC_CAP_8BIT);

        Serial.println("Internal RAM (Heap):");
        Serial.printf("  Total: %u bytes (%.1f KB)\n", totalHeap, totalHeap / 1024.0);
        Serial.printf("  Used: %u bytes (%.1f KB, %.1f%%)\n",
                      usedHeap, usedHeap / 1024.0,
                      (usedHeap * 100.0) / totalHeap);
        Serial.printf("  Free: %u bytes (%.1f KB, %.1f%%)\n",
                      freeHeap, freeHeap / 1024.0,
                      (freeHeap * 100.0) / totalHeap);
        Serial.printf("  Min Free Ever: %u bytes (%.1f KB)\n",
                      minFreeHeap, minFreeHeap / 1024.0);

        // PSRAM (external RAM)
        size_t freePSRAM = heap_caps_get_free_size(MALLOC_CAP_SPIRAM);
        size_t totalPSRAM = heap_caps_get_total_size(MALLOC_CAP_SPIRAM);
        size_t usedPSRAM = totalPSRAM - freePSRAM;
        size_t minFreePSRAM = heap_caps_get_minimum_free_size(MALLOC_CAP_SPIRAM);

        Serial.println("\nExternal RAM (PSRAM):");
        Serial.printf("  Total: %u bytes (%.1f MB)\n", totalPSRAM, totalPSRAM / (1024.0 * 1024.0));
        Serial.printf("  Used: %u bytes (%.1f KB, %.1f%%)\n",
                      usedPSRAM, usedPSRAM / 1024.0,
                      (usedPSRAM * 100.0) / totalPSRAM);
        Serial.printf("  Free: %u bytes (%.1f MB, %.1f%%)\n",
                      freePSRAM, freePSRAM / (1024.0 * 1024.0),
                      (freePSRAM * 100.0) / totalPSRAM);
        Serial.printf("  Min Free Ever: %u bytes (%.1f KB)\n",
                      minFreePSRAM, minFreePSRAM / 1024.0);

        // Memory health warnings
        Serial.println("\nMemory Health:");
        if (freeHeap < 50000)
        {
            Serial.println("  ⚠️  WARNING: Low heap memory (< 50KB)!");
        }
        else if (freeHeap < 100000)
        {
            Serial.println("  ⚡ CAUTION: Heap memory getting low (< 100KB)");
        }
        else
        {
            Serial.println("  ✓ Heap memory OK");
        }

        if (totalPSRAM > 0)
        {
            if (freePSRAM < 1000000)
            {
                Serial.println("  ⚠️  WARNING: Low PSRAM (< 1MB)!");
            }
            else
            {
                Serial.println("  ✓ PSRAM OK");
            }
        }
        else
        {
            Serial.println("  ❌ ERROR: PSRAM not detected!");
        }

        Serial.println("=========================\n");
    }

    /**
     * Check if memory is healthy (enough free space)
     */
    static bool isMemoryHealthy()
    {
        size_t freeHeap = heap_caps_get_free_size(MALLOC_CAP_8BIT);
        size_t freePSRAM = heap_caps_get_free_size(MALLOC_CAP_SPIRAM);

        // Require at least 50KB heap and 1MB PSRAM
        return (freeHeap > 50000) && (freePSRAM > 1000000);
    }

    /**
     * Get free heap in bytes
     */
    static size_t getFreeHeap()
    {
        return heap_caps_get_free_size(MALLOC_CAP_8BIT);
    }

    /**
     * Get free PSRAM in bytes
     */
    static size_t getFreePSRAM()
    {
        return heap_caps_get_free_size(MALLOC_CAP_SPIRAM);
    }

    /**
     * Check if PSRAM is available
     */
    static bool hasPSRAM()
    {
        return heap_caps_get_total_size(MALLOC_CAP_SPIRAM) > 0;
    }

    /**
     * Print a compact one-line memory status
     */
    static void printCompactStatus()
    {
        size_t freeHeap = getFreeHeap();
        size_t freePSRAM = getFreePSRAM();
        Serial.printf("Memory: Heap=%uKB, PSRAM=%uKB\n",
                      freeHeap / 1024, freePSRAM / 1024);
    }
};

#endif // MEMORY_MONITOR_H
