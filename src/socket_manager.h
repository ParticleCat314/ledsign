#pragma once
#include <unistd.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <fcntl.h>
#include <cstring>
#include <string>
#include <iostream>
#include <vector>
#include <csignal>
#include <sys/stat.h>
#include <thread>

#include "constants.h"
#include "sign.h"

void cleanup_and_exit(int) {
    unlink(LedSignConstants::SOCKET_PATH);
    _exit(0);
}

bool write_all(int fd, const std::string& s) {
    const char* p = s.c_str();
    size_t n = s.size();
    while (n) {
        ssize_t k = ::write(fd, p, n);
        if (k <= 0)
            return false;
        p += k;
        n -= (size_t)k;
    }
    return true;
}

bool read_line(int fd, std::string& out) {
    out.clear();
    char buf[256];
    while (true) {
        ssize_t k = ::read(fd, buf, sizeof(buf));
        if (k == 0)
            return !out.empty(); // EOF
        if (k < 0) {
            if (errno == EINTR)
                continue;
            return false;
        }
        for (ssize_t i = 0; i < k; ++i) {
            char c = buf[i];
            if (c == '\n')
                return true;
            out.push_back(c);
            if (out.size() > LedSignConstants::MAX_MESSAGE_SIZE)
                return false; // sanity cap
        }
    }
}


int run_socket_server(Sign& sign) {

    // Create the sign worker thread
    std::thread t;


    // Clean up socket file on crash/ctrl-c
    struct sigaction sa{};
    sa.sa_handler = cleanup_and_exit;
    sigemptyset(&sa.sa_mask);
    sigaction(SIGINT, &sa, nullptr);
    sigaction(SIGTERM, &sa, nullptr);

    // Create, bind, listen
    ::unlink(LedSignConstants::SOCKET_PATH);
    int s = ::socket(AF_UNIX, SOCK_STREAM, 0);
    if (s < 0) {
        perror("socket");
        return 1;
    }

    sockaddr_un addr{};
    addr.sun_family = AF_UNIX;
    std::snprintf(addr.sun_path, sizeof(addr.sun_path), "%s", LedSignConstants::SOCKET_PATH);

    // Set tighter permissions: owner-only
    ::umask(0077);

    if (::bind(s, (sockaddr*)&addr, sizeof(sa_family_t) + std::strlen(addr.sun_path)) < 0) {
        perror("bind");
        return 1;
    }

    // Ensure proper permissions on the socket node
    ::chmod(LedSignConstants::SOCKET_PATH, LedSignConstants::SOCKET_PERMISSIONS);

    if (::listen(s, LedSignConstants::SOCKET_BACKLOG) < 0) {
        perror("listen");
        return 1;
    }

    std::cout << "LED sign daemon listening on " << LedSignConstants::SOCKET_PATH << std::endl;


    while (true) {
        int c = ::accept(s, nullptr, nullptr);
        if (c < 0) {
            if (errno == EINTR)
                continue;
            perror("accept");
            break;
        }

        std::string line;
        if (!read_line(c, line)) {
            write_all(c, "ERR read failed\n");
            ::close(c);
            continue;
        }

        std::string reply;

        if (line == "CLEAR") {
            sign.handleInterrupt(true);
            if (t.joinable())
                t.join();
            sign.clear();
            reply = "OK cleared\n";
        }

        else if (line.substr(0, 3) == "SET") {
            std::string msg = line.substr(3);
            sign.handleInterrupt(true);
            if (t.joinable())
                t.join();
            sign.handleInterrupt(false);
            t = std::thread([&sign, msg]() {
                sign.render(msg);
            });
            reply = "OK setting\n";
        }

        else {
            reply = "ERR unknown command\n";
        }

        write_all(c, reply);
        ::close(c);
    }

    // Ensure thread is properly joined before cleanup
    if (t.joinable()) {
        sign.handleInterrupt(true);
        t.join();
    }

    ::unlink(LedSignConstants::SOCKET_PATH);
    return 0;
}

