#!/usr/bin/env bash
FODEFENSE_SO="${FODEFENSE_SO:?set FODEFENSE_SO to your FODefensePass.so}"
src=""; out=""; compile=0; prev=""
for a in "$@"; do
  case "$a" in -c) compile=1;; *.c) src="$a";; esac
  [ "$prev" = "-o" ] && out="$a"; prev="$a"
done
base="${src##*/}"
if [[ "$compile" == 1 && "$base" == "kem.c" ]]; then
  cargs=(); skip=0
  for a in "$@"; do
    if [ "$skip" = 1 ]; then skip=0; continue; fi
    case "$a" in
      "$src") ;; -c) ;; -o) skip=1;;
      -Wa,*) ;; -funsigned-bitfields) ;;
      *) cargs+=("$a");;
    esac
  done
  ARM_ISYS=$(for d in $(echo | arm-none-eabi-gcc -mcpu=cortex-m4 -mthumb -E -Wp,-v - 2>&1 \
            | sed -n 's/^ \(\/.*\)/\1/p'); do [ -d "$d" ] && printf -- "-isystem %s " "$d"; done)
  bc=$(mktemp --suffix=.bc); dbc=$(mktemp --suffix=.bc)
  trap 'rm -f "$bc" "$dbc"' EXIT
  clang --target=arm-none-eabi $ARM_ISYS "${cargs[@]}" -emit-llvm -c "$src" -o "$bc" || exit 1
  opt -load-pass-plugin="$FODEFENSE_SO" -passes=fo-defense "$bc" -o "$dbc" || exit 1
  clang --target=arm-none-eabi "${cargs[@]}" -c "$dbc" -o "$out"
else
  exec arm-none-eabi-gcc "$@"
fi
