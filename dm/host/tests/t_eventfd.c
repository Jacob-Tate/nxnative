// Event descriptors (hle_net.c): a local counter on Horizon that needs no network. gRPC's wakeup fd (Ocarina of Time, grpc_init): EventFd(0, close-on-exec | non-blocking),
// a write wakes Poll, the read returns and clears the counter, an empty non-blocking read fails with EAGAIN in both numberings, Close frees it. No game needed.
#include "../hle_net.c"
#include <assert.h>
#include <pthread.h>
#include <time.h>
#include <unistd.h>

static int libc_errno;   // the guest C library's errno, which the host sets through __errno_location
static int *errno_loc(void) { return &libc_errno; }
void *guest_sym(const char *name) { return !strcmp(name, "__errno_location") ? (void *)errno_loc : NULL; }
void dm_guest_sleep_ns(int64_t ns) { struct timespec t = {ns / 1000000000, ns % 1000000000}; nanosleep(&t, NULL); }

static int64_t now_ms(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec * 1000 + t.tv_nsec / 1000000; }
static void *writer(void *a) { usleep(50000); assert(h_sk_EventFdWrite(*(int *)a, 1) == 0); return NULL; }

int main(void) {
    int fd = h_sk_EventFd(0, 2 | EFD_NONBLOCK);
    assert(fd >= EFD_BASE);
    unsigned long v = 99;
    assert(h_sk_EventFdRead(fd, &v) == -1 && v == 99);   // empty, non-blocking
    assert(h_sk_GetLastError() == SK_EAGAIN && libc_errno == LIBC_EAGAIN);

    sk_pollfd p[2] = {{fd, SK_POLLIN, 0}, {-1, SK_POLLIN, 0}};
    int64_t t0 = now_ms();
    assert(dm_sk_poll(p, 2, 30) == 0 && p[0].revents == 0);   // nothing written: the timeout passes
    assert(now_ms() - t0 >= 25);

    pthread_t th; pthread_create(&th, NULL, writer, &fd);
    t0 = now_ms();
    assert(dm_sk_poll(p, 1, 5000) == 1 && p[0].revents == SK_POLLIN);   // woken by the write, long before the timeout
    assert(now_ms() - t0 < 2000);
    pthread_join(th, NULL);
    assert(h_sk_EventFdWrite(fd, 2) == 0);
    assert(h_sk_EventFdRead(fd, &v) == 0 && v == 3);   // the counter, cleared
    assert(h_sk_EventFdRead(fd, &v) == -1);

    int sem = h_sk_EventFd(2, EFD_SEMAPHORE | EFD_NONBLOCK);   // semaphore mode: one at a time
    assert(h_sk_EventFdRead(sem, &v) == 0 && v == 1 && h_sk_EventFdRead(sem, &v) == 0 && v == 1 && h_sk_EventFdRead(sem, &v) == -1);

    sk_pollfd w = {sem, SK_POLLOUT, 0};
    assert(dm_sk_poll(&w, 1, 0) == 1 && w.revents == SK_POLLOUT);   // always writable

    assert(h_sk_Close(fd) == 0 && h_nsk_Close(sem) == 0);
    assert(h_sk_Close(fd) == -1 && h_sk_GetLastError() == SK_ENETDOWN);   // closed: not a descriptor any more, as any other socket
    sk_pollfd gone = {fd, SK_POLLIN, 0};
    assert(dm_sk_poll(&gone, 1, 0) == -1);   // other descriptors fail Poll, as before
    assert(h_sk_EventFdWrite(fd, 1) == -1 && libc_errno == 9);
    puts("t_eventfd: ok");
    return 0;
}
