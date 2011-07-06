#
# common.py
#
# Copyright (C) 2011 Pedro Algarvio <ufs@ufsoft.org>
#
# Basic plugin template created by:
# Copyright (C) 2008 Martijn Voncken <mvoncken@gmail.com>
# Copyright (C) 2007-2009 Andrew Resch <andrewresch@gmail.com>
# Copyright (C) 2009 Damien Churchill <damoxc@gmail.com>
# Copyright (C) 2010 Pedro Algarvio <pedro@algarvio.me>
#
# Deluge is free software.
#
# You may redistribute it and/or modify it under the terms of the
# GNU General Public License, as published by the Free Software
# Foundation; either version 3 of the License, or (at your option)
# any later version.
#
# deluge is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with deluge.    If not, write to:
# 	The Free Software Foundation, Inc.,
# 	51 Franklin Street, Fifth Floor
# 	Boston, MA  02110-1301, USA.
#
#    In addition, as a special exception, the copyright holders give
#    permission to link the code of portions of this program with the OpenSSL
#    library.
#    You must obey the GNU General Public License in all respects for all of
#    the code used other than OpenSSL. If you modify file(s) with this
#    exception, you may extend this exception to your version of the file(s),
#    but you are not obligated to do so. If you do not wish to do so, delete
#    this exception statement from your version. If you delete this exception
#    statement from all source files in the program, then also delete it here.
#


__all__ = ['get_resource', 'get_manhole', 'create_manhole']

def get_resource(filename):
    import pkg_resources, os
    return pkg_resources.resource_filename("deluge.plugins.manhole", os.path.join("data", filename))


def get_manhole():
    return Manhole._instance

def create_manhole(config, namespace):
    return Manhole(config, **namespace)
#    global __MANHOLE_INSTANCE
#    if __MANHOLE_INSTANCE is not None:
#        __MANHOLE_INSTANCE.update_namespace(**namespace)
#        return __MANHOLE_INSTANCE
#
#    __MANHOLE_INSTANCE = Manhole(config, **namespace)
#    return __MANHOLE_INSTANCE


import logging
from twisted.internet import protocol, reactor
from twisted.conch import telnet, manhole
from twisted.conch.insults import insults
from twisted.conch.manhole_tap import _StupidRealm, makeTelnetProtocol
from twisted.cred import portal, checkers
from twisted.python import text
from rlcompleter import Completer

log = logging.getLogger(__name__)


class EnhancedColoredManhole(manhole.ColoredManhole):
    def find_common(self, l):
        """
        Find common parts in thelist items::

            'ab' for ['abcd','abce','abf']

        requires an ordered list
        """
        if len(l) == 1:
            return l[0]

        init = l[0]
        for item in l[1:]:
            for i, (x,y) in enumerate(zip(init, item)):
                if x != y:
                    init = "".join(init[:i])
                    break

            if not init:
                return None
        return init

    def handle_TAB1(self):
        head_line, tail_line = self.currentLineBuffer()
        search_line = head_line

        completer = Completer(self.namespace)

        def find_term(line):
            chrs = []
            attr = False
            for c in reversed(line):
                if c == '.':
                    attr = True
                if not c.isalnum() and c not in ('_', '.'):
                    break
                chrs.insert(0, c)
            return ''.join(chrs), attr

        search_term, attrQ = find_term(search_line)

        if not search_term:
            return manhole.Manhole.handle_TAB(self)

        if attrQ:
            matches = completer.attr_matches(search_term)
            matches = list(set(matches))
            matches.sort()
        else:
            matches = completer.global_matches(search_term)

        def same(*args):
            if len(set(args)) == 1:
                return args[0]
            return False

        def progress(rem):
            letters = []
            while True:
                letter = same(*[elm.pop(0) for elm in rem if elm])
                if letter:
                    letters.append(letter)
                else:
                    return letters

        if matches is not None:
            rem = [list(s.partition(search_term)[2]) for s in matches]
            more_letters = progress(rem)
#            print 'LEN MATCHES', len(matches), more_letters
#            if len(matches) == 1:
#                length = len(search_line)
#                self.lineBuffer = self.lineBuffer[:-length]
#                self.lineBuffer.extend([matches[0]]+more_letters)
#                self.lineBufferIndex = len(self.lineBuffer)
            if len(matches) > 1:
                match_str = "%s \t\t" * len(matches) % tuple(matches)
                match_rows = text.greedyWrap(match_str)
#                line = self.lineBuffer
                self.terminal.nextLine()
                self.terminal.saveCursor()
                for row in match_rows:
                    self.addOutput(row, True)
                if tail_line:
                    self.terminal.cursorBackward(len(tail_line))
                    self.lineBufferIndex -= len(tail_line)
#            self.addOutput("".join(more_letters), True)
            self._deliverBuffer(more_letters)



    def handle_TAB(self):
        necessarypart = "".join(self.lineBuffer).split(' ')[-1]
        completer = Completer(self.namespace)
        if completer.complete(necessarypart, 0):
            matches = list(set(completer.matches)) # has multiples

            if len(matches) == 1:
                length = len(necessarypart)
                self.lineBuffer = self.lineBuffer[:-length]
                self.lineBuffer.extend(matches[0])
                self.lineBufferIndex = len(self.lineBuffer)
            else:
                matches.sort()
                commons = self.find_common(matches)
                if commons:
                    length = len(necessarypart)
                    self.lineBuffer = self.lineBuffer[:-length]
                    self.lineBuffer.extend(commons)
                    self.lineBufferIndex = len(self.lineBuffer)

                self.terminal.nextLine()
                while matches:
                    matches, part = matches[4:], matches[:4]
                    for item in part:
                        self.terminal.write('%s' % item.ljust(30))
                    self.terminal.write('\n')
                self.terminal.nextLine()

            self.terminal.eraseLine()
            self.terminal.cursorBackward(self.lineBufferIndex + 5)
            self.terminal.write("%s%s" % (self.ps[self.pn], "".join(self.lineBuffer)))

    def terminalSize(self, width, height):
#        print 'TERMINAL SIZE CALLED', width, height
        super(EnhancedColoredManhole, self).terminalSize(width, height)

    def _deliverBuffer(self, buf):
#        print '_deliverBuffer CALLED', buf
        super(EnhancedColoredManhole, self)._deliverBuffer(buf)
#        self.terminal.eraseLine()
#        self.terminal.cursorBackward(self.lineBufferIndex + 5)
#        self.drawInputLine()
        self.lineBufferIndex -= 1
#        self.terminal.cursorBackward()
#        self.terminal.deleteCharacter()
        self.characterReceived(self.lineBuffer.pop(), False)


    def characterReceived(self, ch, moreCharactersComing):
#        print 'characterReceived CALLED', ch, 'CLB', self.currentLineBuffer()
        super(EnhancedColoredManhole, self).characterReceived(ch, moreCharactersComing)


class StupidRealm(_StupidRealm):
    def update_namespace(self, namespace):
        self.protocolKwArgs.update(namespace)

class Manhole(object):
    def __new__(cls, config, **namespace):
        if getattr(cls, '_instance', None) is not None:
            cls._instance.update_namespace(namespace)
            return cls._instance
        cls._instance = super(Manhole, cls).__new__(cls)
        return cls._instance

    def __init__(self, config, **namespace):
        self.config = config

        self.realm = self._get_realm(**namespace)
        self.portal = self._get_portal()
        self.factory = protocol.ServerFactory()
        self.factory.protocol = makeTelnetProtocol(self.portal)
        self.service = None

    def start(self):
        log.debug("Manhole Telnet Server Starting...")
        self.service = reactor.listenTCP(
            self.config['port'], self.factory, interface=self.config['host']
        )

    def stop(self):
        log.debug("Manhole Telnet Server Stopping...")
        if self.service:
            self.service.stopListening()
            self.service = None

    def update_namespace(self, namespace):
        self.realm.update_namespace(namespace)

    def _get_realm(self, **namespace):
        return StupidRealm(telnet.TelnetBootstrapProtocol,
                           insults.ServerProtocol,
                           EnhancedColoredManhole,
                           namespace)

    def _get_checker(self):
        return checkers.InMemoryUsernamePasswordDatabaseDontUse(
            **{self.config['username']: self.config['password']}
        )

    def _get_portal(self):
        return portal.Portal(self.realm, [self._get_checker()])
