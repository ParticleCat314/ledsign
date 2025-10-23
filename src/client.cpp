#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>
#include <cstring>
#include <string>
#include <iostream>
#include "constants.h"

bool write_all(int fd, const std::string& s) {
    const char* p = s.c_str();
    size_t n = s.size();
    while (n) {
        ssize_t k = ::write(fd, p, n);
        if (k <= 0) return false;
        p += k; n -= (size_t)k;
    }
    return true;
}

int main(int argc, char** argv) {
    std::string cmd = argv[1];
    std::string line;

    if (cmd == "CLEAR") {
        line = "CLEAR\n";
        printf("Sending command: %s", line.c_str());
    }
    else if (cmd == "SET") {
        line = cmd + argv[2] + "\n";
        printf("Sending command: %s", line.c_str());
    }
    else {
        std::cerr << "unknown command\n";
        return 2;
    }

    int s = ::socket(AF_UNIX, SOCK_STREAM, 0);
    if (s < 0) { perror("socket"); return 1; }

    sockaddr_un addr{}; addr.sun_family = AF_UNIX;
    std::snprintf(addr.sun_path, sizeof(addr.sun_path), "%s", LedSignConstants::SOCKET_PATH);

    if (::connect(s, (sockaddr*)&addr, sizeof(sa_family_t) + std::strlen(addr.sun_path)) < 0) {
        perror("connect"); return 1;
    }
    if (!write_all(s, line)) { std::cerr << "write failed\n"; return 1; }

    // Read one line reply
    std::string reply; reply.reserve(256);
    char ch;
    while (true) {
        ssize_t k = ::read(s, &ch, 1);
        if (k <= 0) break;
        if (ch == '\n') break;
        reply.push_back(ch);
    }
    ::close(s);
    std::cout << reply << "\n";
    return 0;
}
