from enum import Enum
from typing import Callable


class TokenKind(Enum):
    Unknown = 0
    Int = 5
    Identifier = 10
    String = 20
    Punctuater = 30


class Token:
    def __init__(self, kind: TokenKind, s: str, pos: int):
        self.kind = kind
        self.str = s
        self.position = pos


class Lexer:
    def __init__(self, source: str):
        self.source = source
        self.position = 0
        self.length = len(self.source)

    def check(self) -> bool:
        return self.position < self.length

    def peek(self) -> str:
        return self.source[self.position]

    def pass_space(self) -> None:
        while self.check() and self.peek().isspace():
            self.position += 1

    def pass_while(self, fncond: Callable[[str], bool]) -> tuple[int, str]:
        pos = self.position

        while self.check() and fncond(self.peek()):
            self.position += 1

        return pos, self.source[pos : self.position]

    def lex(self) -> list[Token]:
        ret: list[Token] = []

        self.pass_space()

        while self.check():
            ch = self.peek()
            tok = Token(TokenKind.Unknown, "", self.position)

            if ch.isdigit():
                tok.position, tok.str = self.pass_while(str.isdigit)

        return ret


class ParserBase:
    def __init__(self, tokens: list[Token]):
        self.index = 0
        self.tokens = tokens

    def get_cur_token(self) -> Token:
        return self.tokens[self.index]


class MakefileParser(ParserBase):
    def __init__(self, tokens: list[Token]) -> None:
        super().__init__(tokens)


src = """
TARGET		?= 	metro
DBGPREFIX	?=	d

TOPDIR		?= 	$(CURDIR)
BUILD		:= 	build
INCLUDE		:= 	include
SOURCE		:= 	src \
				src/Evaluator

CC			:=	gcc
CXX			:=	g++

OPTI		?=	-O0 -g -D_METRO_DEBUG_
COMMON		:=	$(OPTI) -Wall -Wextra -Wno-switch $(INCLUDES)
CFLAGS		:=	$(COMMON) -std=c17
CXXFLAGS	:=	$(COMMON) -std=c++20
LDFLAGS		:=

%.o: %.c
	@echo $(notdir $<)
	@$(CC) -MP -MMD -MF $*.d $(CFLAGS) -c -o $@ $<

%.o: %.cpp
	@echo $(notdir $<)
	@$(CXX) -MP -MMD -MF $*.d $(CXXFLAGS) -c -o $@ $<

ifneq ($(BUILD), $(notdir $(CURDIR)))

CFILES			= $(notdir $(foreach dir,$(SOURCE),$(wildcard $(dir)/*.c)))
CXXFILES		= $(notdir $(foreach dir,$(SOURCE),$(wildcard $(dir)/*.cpp)))

export OUTPUT		= $(TOPDIR)/$(TARGET)$(DBGPREFIX)
export VPATH		= $(foreach dir,$(SOURCE),$(TOPDIR)/$(dir))
export INCLUDES		= $(foreach dir,$(INCLUDE),-I$(TOPDIR)/$(dir))
export OFILES		= $(CFILES:.c=.o) $(CXXFILES:.cpp=.o)

.PHONY: $(BUILD) all re clean

all: $(BUILD)
	@$(MAKE) --no-print-directory -C $(BUILD) -f $(TOPDIR)/Makefile

release: $(BUILD)
	@$(MAKE) --no-print-directory OUTPUT="$(TOPDIR)/$(TARGET)" OPTI="-O8" \
		LDFLAGS="-Wl,--gc-sections,-s" -C $(BUILD) -f $(TOPDIR)/Makefile

$(BUILD):
	@[ -d $@ ] || mkdir -p $@

clean:
	rm -rf $(TARGET) $(TARGET)$(DBGPREFIX) $(BUILD)

re: clean all

else

DEPENDS		:= $(OFILES:.o=.d)

$(OUTPUT): $(OFILES)
	@echo linking...
	@$(CXX) -pthread $(LDFLAGS) -o $@ $^

-include $(DEPENDS)

endif
"""

tokens = Lexer(src).lex()

m = MakefileParser(tokens)
