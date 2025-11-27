#ifndef PSRAM_ALLOCATOR_H
#define PSRAM_ALLOCATOR_H

#include <Arduino.h>
#include <cstddef>
#include <esp_heap_caps.h>

/**
 * Custom allocator for std::vector that uses PSRAM instead of regular heap
 * This is critical for large data buffers (30,000+ samples)
 *
 * ESP32-S3 has ~400KB internal RAM but 8MB PSRAM
 * Using PSRAM prevents heap exhaustion during data collection
 */
template <typename T>
class PSRAMAllocator
{
public:
    using value_type = T;
    using pointer = T *;
    using const_pointer = const T *;
    using reference = T &;
    using const_reference = const T &;
    using size_type = std::size_t;
    using difference_type = std::ptrdiff_t;

    template <typename U>
    struct rebind
    {
        using other = PSRAMAllocator<U>;
    };

    PSRAMAllocator() noexcept {}

    template <typename U>
    PSRAMAllocator(const PSRAMAllocator<U> &) noexcept {}

    ~PSRAMAllocator() noexcept {}

    pointer allocate(size_type n)
    {
        if (n == 0)
            return nullptr;

        // Allocate from PSRAM using ESP-IDF heap caps
        pointer p = static_cast<pointer>(
            heap_caps_malloc(n * sizeof(T), MALLOC_CAP_SPIRAM));

        if (!p)
        {
            Serial.printf("ERROR: PSRAM allocation failed! Requested: %u bytes\n",
                          n * sizeof(T));
            throw std::bad_alloc();
        }

        Serial.printf("PSRAM allocated: %u bytes (%u items)\n",
                      n * sizeof(T), n);

        return p;
    }

    void deallocate(pointer p, size_type n) noexcept
    {
        if (p)
        {
            heap_caps_free(p);
            Serial.printf("PSRAM freed: %u bytes (%u items)\n",
                          n * sizeof(T), n);
        }
    }

    template <typename U, typename... Args>
    void construct(U *p, Args &&...args)
    {
        new (p) U(std::forward<Args>(args)...);
    }

    template <typename U>
    void destroy(U *p)
    {
        p->~U();
    }
};

// Comparison operators
template <typename T1, typename T2>
bool operator==(const PSRAMAllocator<T1> &, const PSRAMAllocator<T2> &) noexcept
{
    return true;
}

template <typename T1, typename T2>
bool operator!=(const PSRAMAllocator<T1> &, const PSRAMAllocator<T2> &) noexcept
{
    return false;
}

#endif // PSRAM_ALLOCATOR_H
